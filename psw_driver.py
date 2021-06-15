import pyvisa

rm=pyvisa.ResourceManager()

# res = rm.open_resource('TCPIP0::169.254.4.61::inst0::INSTR')#网口
psw = rm.open_resource('ASRL3::INSTR')#串口

# print(psw.query("*IDN?"))#通用
# print(psw.query("meas:volt:dc?"))#通用
# print(psw.query("meas:curr:dc?"))#通用
# print(psw.write("SOUR:VOLT:LEV:IMM:AMPL 0.57"))#通用
# psw = rm.open_resource('ASRL3::INSTR')#串口
# psw.close()
# psw.open()
# for i in range(3):
#     print(psw.write("SOUR:VOLT:LEV:IMM:AMPL 0.56"))#通用
#     print(psw.write("SOUR:VOLT:LEV:IMM:AMPL 0.57"))#通用
#     print(psw.query("meas:volt:dc?"))#通用
#     print(psw.query("meas:curr:dc?"))#通用
# voltage = float(psw.query("meas:volt:dc?"))
# print(voltage)
# current = psw.query("meas:curr:dc?")
# set_voltage = 0.666
# print(psw.write("outp:trig:1"))
# print(psw.write("trig:output"))
# print(psw.write("outp:0"))
# print(psw.query("outp?"))
# # print(psw.write("outp:0"))
# print(psw.write("trig:output:sour"))
# print(psw.write("syst:conf:outp:pon 0"))
# print(psw.write("init:outp"))
# # print(psw.write("outp:0"))
# print(psw.write("outp:trig:0"))
# print(psw.write("trig:output"))
# print(psw.query("trig:output:sour?"))

# print(psw.write("TRIG:TRAN:SOUR IMM"))
# print(psw.write("CURR:TRIG MAX"))
# print(psw.write("VOLT:TRIG 5"))
# print(psw.write("INIT:NAME TRAN"))

# print(psw.write("TRIG:OUTP:SOUR IMM"))
print(psw.write("OUTP:TRIG 0"))
print(psw.write("INIT:NAME OUTP"))

print(psw.write("OUTP:TRIG 1"))
print(psw.write("INIT:NAME OUTP"))