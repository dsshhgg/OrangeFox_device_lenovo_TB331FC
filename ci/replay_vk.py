#!/usr/bin/env python3
"""Compile unmodified slices of the supplied events.cpp and call its actual vk_modify.
No Android runtime or device access. Stub framebuffer geometry/haptics only;
synthetic inputs and real evdev streams share the exact same executable.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--capture', type=Path)
p.add_argument('--cxx', default='g++')
p.add_argument('--observe', action='store_true', help='report but do not enforce expected outputs')
p.add_argument('--himax-tests', action='store_true', help='also require TB331FC aggregate-contact behavior')
a = p.parse_args()
s = a.source.read_text(encoding='utf-8')
def slice_between(start, end):
    left = s.index(start)
    return s[left:s.index(end,left)]

types = {'EV_SYN':0,'EV_KEY':1,'EV_REL':2,'EV_ABS':3}
codes = {'SYN_REPORT':0,'ABS_X':0,'ABS_Y':1,'REL_X':0,'REL_Y':1,'REL_Z':2,'BTN_LEFT':272,'BTN_TOUCH':330,'ABS_MT_SLOT':47,'ABS_MT_TOUCH_MAJOR':48,'ABS_MT_WIDTH_MAJOR':50,'ABS_MT_POSITION_X':53,'ABS_MT_POSITION_Y':54,'ABS_MT_TRACKING_ID':57,'ABS_MT_PRESSURE':58}
S = 'EV_SYN SYN_REPORT 0'
def evs(*lines):
    return [(0,*line.split()) for line in lines]
press = evs('EV_ABS ABS_MT_TRACKING_ID 17','EV_ABS ABS_MT_POSITION_X 1000','EV_ABS ABS_MT_POSITION_Y 2000',S)
end = 'EV_ABS ABS_MT_TRACKING_ID -1'
major = 'EV_ABS ABS_MT_TOUCH_MAJOR 0'
pressure = 'EV_ABS ABS_MT_PRESSURE 0'
D=lambda x,y: (3,1,(x<<16)|y)
U=lambda x,y: (3,0,(x<<16)|y)
xy = D(99,199)
updated = D(199,199)
# Each case starts in a new process, so the actual source's static state resets.
checks = {
    'tracking_only': (press+evs(end,S), [xy,U(99,199)]),
    'major_zero_after_tracking': (press+evs(end,major,S), [xy,U(99,199)]),
    'pressure_zero_after_tracking': (press+evs(end,pressure,S), [xy,U(99,199)]),
    'both_zeros_after_tracking': (press+evs(end,major,pressure,S)+press+evs(end,pressure,S), [xy,U(99,199)]*2),
    'zeros_before_tracking': (press+evs(major,pressure,end,S), [xy,U(99,199)]),
    'single_axis_update': (press+evs('EV_ABS ABS_MT_POSITION_X 2000',S,end,S), [xy,updated,U(199,199)]),
    'legacy_major_zero': (press+evs(major,S), [xy,U(99,199)]),
    'legacy_pressure_zero': (press+evs(pressure,S), [xy,U(99,199)]),
    'standalone_pen_abs_xy': ([(1,*l[1:]) for l in evs('EV_ABS ABS_X 1000','EV_ABS ABS_Y 2000',S,'EV_ABS ABS_X 2000',S,S)], [xy,updated,U(199,199)]),
    'mouse_passthrough': (evs('EV_REL REL_X 30','EV_REL REL_Y -5','EV_KEY BTN_LEFT 1','EV_KEY BTN_LEFT 0'), [(2,0,30),(2,1,-5),(1,272,1),(1,272,0)]),
    'virtual_key_release': ([(2,*l[1:]) for l in press+evs(end,pressure,S)], [(1,158,1),(1,158,0)]),
}
if a.himax_tests:
    # Indices 0/2 select Himax (with/without virtual keys); index 1 is pen or
    # generic legacy touch, and index 3 is the unchanged mouse path.
    legacy = {'tracking_only','zeros_before_tracking','legacy_major_zero','legacy_pressure_zero','single_axis_update'}
    for name in legacy:
        events, want = checks[name]
        checks[name] = ([(1,t,c,v) for _,t,c,v in events], want)
    checks['mouse_passthrough'] = ([(3,t,c,v) for _,t,c,v in checks['mouse_passthrough'][0]], checks['mouse_passthrough'][1])
    bdown='EV_KEY BTN_TOUCH 1'; bup='EV_KEY BTN_TOUCH 0'
    down=(1,330,1); up=(1,330,0)
    first=press[:-1]+evs(bdown,S)
    for name, z in [('major_zero_after_tracking',[major]),('pressure_zero_after_tracking',[pressure]),('both_zeros_after_tracking',[major,pressure])]:
        gesture=first+evs(end,*z,bup,S)
        checks[name] = (gesture*2, [down,xy,up,U(99,199)]*2)
    checks['virtual_key_release'] = ([(2,t,c,v) for _,t,c,v in first+evs(end,pressure,bup,S)], [down,(1,158,1),up,(1,158,0)])
    checks['interleaved_pen_syn'] = (first + evs(end,major,pressure,bup) + [(1,'EV_SYN','SYN_REPORT','0')] + evs(S), [down,xy,up,U(99,199)])
    multi=first+evs('EV_ABS ABS_MT_SLOT 1','EV_ABS ABS_MT_TRACKING_ID 18','EV_ABS ABS_MT_POSITION_X 9000','EV_ABS ABS_MT_POSITION_Y 9000',S,'EV_ABS ABS_MT_SLOT 0',end,major,pressure,'EV_ABS ABS_MT_SLOT 1','EV_ABS ABS_MT_POSITION_X 9500',S,end,major,pressure,bup,S)
    checks['nonfinal_slot_end'] = (multi, [down,xy,D(899,899),D(949,899),up,U(949,899)])
    checks['aggregate_release_without_axis_changes'] = (first+evs(bup,S,S), [down,xy,up,U(99,199)])
observe = {}
if a.capture:
    data=a.capture.read_bytes()
    text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8')
    raw=[]
    for line in text.splitlines():
        m = re.match(r'^\[\s*\d+\.\d+\]\s+(EV_\S+)\s+(\S+)\s+(\S+)',line)
        if not m:
            if 'EV_' in line: raise ValueError(line)
            continue
        t,c,val=m.groups()
        if val in ('DOWN','UP'):
            val='1' if val=='DOWN' else '0'
        else:
            n=int(val,16)
            val=str(n if n < 2**31 else n-2**32)
        raw.append((0,t,c,val))
    last=next(i for i,(_,t,c,v) in enumerate(raw) if c=='ABS_MT_TRACKING_ID' and v=='-1')
    stop=next(i for i,(_,t,c,v) in enumerate(raw[last:],last) if c=='SYN_REPORT')+1
    observe['capture_full_ev2']=raw
    # Assert exact output count and coordinate on first release, without assuming
    # any later multi-slot frames map to more than one UI contact.
    observe['capture_first_release']=raw[:stop]

header = '''#include <iostream>
#include <cstring>
struct input_absinfo { int value, minimum, maximum, fuzz, flat, resolution; };
struct input_event { unsigned short type, code; int value; };
struct pollfd;
#define TW_NO_HAPTICS
'''
header+='\n'.join(f'#define {x} {y}' for x,y in (types|{x:y for x,y in codes.items() if not x.startswith('ABS_MT_') and x!='SYN_REPORT'}).items())+'\n'
body = slice_between('#ifndef SYN_REPORT','static struct pollfd ev_fds') + slice_between('static inline int ABS','int write_to_file') + '''
int gr_fb_width() { return 1200; }
int gr_fb_height() { return 1920; }
''' + slice_between('static int vk_tp_to_screen','\nint ev_get(')
main = '''
int main(int argc, char**) {
    ev dev[4]{};
    if (argc > 1) {
        std::strcpy(dev[0].deviceName, "himax-touchscreen");
        std::strcpy(dev[2].deviceName, "himax-touchscreen");
    }
    std::strcpy(dev[1].deviceName, "himax-stylus");
    for (auto& d : dev) {
        d.p.xi.maximum = d.mt_p.xi.maximum = 11999;
        d.p.yi.maximum = d.mt_p.yi.maximum = 19199;
    }
    virtualkey vk{158, 99, 199, 40, 40};
    dev[2].vks = &vk; dev[2].vk_count = 1;
    int idx; input_event e{};
    while (std::cin >> idx >> e.type >> e.code >> e.value) {
        if (vk_modify(&dev[idx], &e) == 0)
            std::cout << e.type << ' ' << e.code << ' ' << e.value << '\\n';
    }
}
'''
failed=0
with tempfile.TemporaryDirectory() as temp:
    cpp=Path(temp)/'replay.cpp'; exe=Path(temp)/'replay.exe'
    cpp.write_text(header+body+main,encoding='utf-8')
    subprocess.run([a.cxx,'-std=c++17','-O2',str(cpp),'-o',str(exe)],check=True)
    def replay(events):
        lines=[f'{d} {types[t]} {codes[c]} {v}\n' for d,t,c,v in events]
        r=subprocess.run([str(exe)]+(['himax'] if a.himax_tests else []),input=''.join(lines),text=True,capture_output=True,check=True)
        return [tuple(map(int,l.split())) for l in r.stdout.splitlines()]
    for name,(events,want) in checks.items():
        got=replay(events)
        ok=got==want
        failed+=not ok
        print(f'{"PASS" if ok else "FAIL"} {name}: expected={want} actual={got}')
    for name,events in observe.items():
        got=replay(events)
        counts=Counter((t,c) for t,c,v in got)
        print(f'OBS {name}: inputs={len(events)} outputs={len(got)} by_type_code={dict(counts)} last={got[-3:]}')
        if name=='capture_full_ev2' and a.himax_tests:
            # Verify the emitted touch-up belongs to each final-contact UP
            # frame, not solely that the total happens to match.
            expected = sum(c=='BTN_TOUCH' and v=='0' for _,t,c,v in events)
            pending = False; unexpected = 0
            for t,c,v in got:
                if (t,c)==(1,330):
                    unexpected += pending
                    pending = v == 0
                elif (t,c)==(3,0):
                    unexpected += not pending
                    pending = False
            ok=not pending and unexpected==0 and counts[3,0]==expected
            failed+=not ok
            print(f'{"PASS" if ok else "FAIL"} aggregate_capture: expected={expected} actual={counts[3,0]} unexpected={unexpected}')
        if name=='capture_first_release':
            prior=replay(events[:last]); assert prior and prior[-1][:2]==(3,1)
            want=prior+[(1,330,0),(3,0,prior[-1][2])]
            ok=want==got
            failed+=not ok
            print(f'{"PASS" if ok else "FAIL"} exact_capture_first_release: expected_tail={want[-3:]} actual_tail={got[-3:]}')
print(f'checks_failed={failed}')
raise SystemExit(bool(failed) and not a.observe)
