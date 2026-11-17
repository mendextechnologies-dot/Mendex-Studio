import subprocess
from pathlib import Path

asc_content = """Version 4
SHEET 1 1280 800
WIRE 64 128 64 64
WIRE 64 64 256 64
WIRE 256 64 256 128
WIRE 256 64 416 64
WIRE 416 64 416 96
WIRE 64 224 64 288
WIRE 256 192 256 224
WIRE 416 160 416 192
WIRE 416 192 256 192
WIRE 256 192 256 256
WIRE 256 320 256 384
WIRE 64 288 256 384
WIRE 256 384 416 384
WIRE 160 288 240 288
WIRE 160 352 160 384
WIRE 256 384 160 384
WIRE 576 128 576 64
WIRE 576 64 688 64
WIRE 688 64 688 128
WIRE 576 192 576 384
WIRE 576 384 688 384
WIRE 688 192 688 256
WIRE 688 256 784 256
WIRE 784 256 784 320
WIRE 784 384 784 416
WIRE 880 256 976 256
WIRE 976 256 976 320
WIRE 976 384 976 416
WIRE 784 416 976 416
WIRE 688 384 784 416
FLAG 64 288 0
FLAG 576 384 0
FLAG 784 416 0
FLAG 256 64 IN
FLAG 256 192 PRI_DRAIN
FLAG 160 288 GATE
FLAG 688 128 SEC_ANODE
FLAG 976 256 VOUT
FLAG 416 192 SNUB_NODE
SYMBOL voltage 64 112 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName V1
SYMATTR Value 24
SYMBOL voltage 160 272 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName VG
SYMATTR Value PULSE(0 10 0 10n 10n 4.08u 10u)
SYMBOL ind 240 112 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName L1
SYMATTR Value 474.42u
SYMBOL ind 672 112 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName L2
SYMATTR Value 1.61H
SYMBOL nmos 240 256 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName M1
SYMATTR Value NMOS_SW
SYMBOL diode 400 96 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName D_SNUB
SYMATTR Value DFAST
SYMBOL cap 768 320 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName C_OUT
SYMATTR Value 220n
SYMATTR SpiceLine IC=1000
SYMBOL res 960 304 R0
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName R_LOAD
SYMATTR Value 1Meg
SYMBOL diode 672 240 R270
WINDOW 123 0 0 Left 2
WINDOW 39 0 0 Left 2
SYMATTR InstName D1
SYMATTR Value HVSiC
TEXT 40 480 Left 2 !K1 L1 L2 0.998
TEXT 40 520 Left 2 !.model NMOS_SW VDMOS(Ron=0.003 Qg=32n Vto=2.5)
TEXT 40 560 Left 2 !.model DFAST D(Is=1e-9 Rs=0.1 Cjo=5p Bv=600)
TEXT 40 600 Left 2 !.model HVSiC D(Is=1e-12 Rs=0.5 Cjo=10p Bv=3300)
TEXT 40 640 Left 2 !.tran 0 2m 1.5m 100n uic
TEXT 40 680 Left 2 !.meas TRAN Vout_avg AVG V(VOUT) FROM 1.8m TO 2m
TEXT 40 720 Left 2 !.meas TRAN Vout_ripple PARAM ((Vout_max - Vout_min) / Vout_avg) * 100
"""

test_asc = Path("scratch/test_flyback.asc")
test_asc.write_text(asc_content, encoding="utf-8")
print("Wrote test_flyback.asc")

ltspice_exe = Path(r"C:\Program Files\ADI\LTspice\LTspice.exe")
if ltspice_exe.exists():
    cmd = [str(ltspice_exe), "-b", "-ascii", str(test_asc.resolve())]
    print("Running:", cmd)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    print("Return code:", res.returncode)
    raw = test_asc.with_suffix(".raw")
    log = test_asc.with_suffix(".log")
    print("Raw exists?:", raw.exists())
    print("Log exists?:", log.exists())
    if log.exists():
        print("Log content:\n", log.read_text()[:400])
