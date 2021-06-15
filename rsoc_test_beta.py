import serial
import binascii
import time
import pyqtgraph as pg
import array
import numpy as np
import threading
from pyqtgraph.Qt import QtGui,QtCore,QtWidgets
import sys
import pyvisa
import os
busy=False
rate=5
times=np.array([])
# mode=True # 电池模式
if not os.path.exists("./output"):
    os.mkdir("./output")
def crc(data:str)->str:
    nums=data.split(" ")
    ret=0
    for num in nums:
        ret+=int(num,16)
    return str(hex(ret))[-2:]
def readnum(line:str,index:int)->int:
    start=index*4+3
    return int(line[(start+3)*2:(start+3)*2+2]+line[(start+2)*2:(start+2)*2+2]+line[(start+1)*2:(start+1)*2+2]+line[start*2:start*2+2],16)
def writenum(num:float)->str:
    int_num=int(num*10000)
    hex_num=hex(int_num)
    hex_num=hex_num[2:]
    buf=hex_num
    for i in range(8-len(hex_num)):
        buf='0'+buf
    ret=""
    for i in range(3,-1,-1):
        ret+=buf[i*2:i*2+2]+' '
    return ret

def query(ser,input_data:str)->str:
    global busy
    while busy:
        time.sleep(0.1)
    busy=True
    data=bytes.fromhex(input_data+crc(input_data))
    ser.write(data)
    line = binascii.b2a_hex(ser.read(26))
    # print(line)
    busy=False
    return line
def remote_switch(on:bool):
    if on:
        query(ser,'AA 00 20 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
    else:
        query(ser,'AA 00 20 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
def load_switch(on:bool):
    if on:
        query(ser,'AA 00 21 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
    else:
        query(ser,'AA 00 21 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
def read_vcp()->list:
    output=query(ser,'AA 00 5F 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
    voltage=readnum(output,0)/1000.
    current=readnum(output,1)/10000.
    power=readnum(output,2)/1000.
    return [voltage,current,power]
def set_load_current(current:float):
    hex_current=writenum(current)
    # remote_switch(True)
    input_data='AA 00 2A '+hex_current+'00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
    query(ser,input_data)
    # remote_switch(False)

def pws_read_voltage(psw)->float:
    return float(psw.query("meas:volt:dc?"))
def pws_read_current(psw)->float:
    return float(psw.query("meas:curr:dc?"))
def pws_set_voltage(psw,voltage:float):
    psw.write("SOUR:VOLT:LEV:IMM:AMPL "+"{:.2f}".format(voltage))
def pws_output_on(psw,on:bool):
    if on:
        psw.write("OUTP:TRIG 1")
    else:
        psw.write("OUTP:TRIG 0")
    psw.write("INIT:NAME OUTP")

class SSOFC(QtGui.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        # self.setGeometry(0, 0, 1000, 800)
        self.setWindowTitle(u'可逆固体氧化物电池综合能源系统测试平台')
        self.resize(1000,800)
        self.setWindowIcon(QtGui.QIcon('./icon2.ico'))
        self.show()
    def closeEvent(self,event):
        ser.close()#关闭端口
        event.accept()
class PaintVCP(QtGui.QWidget):
    def __init__(self):
        super().__init__()
        self.max_power = 200.
        rm=pyvisa.ResourceManager()
        self.psw = rm.open_resource('ASRL3::INSTR')#串口
        pws_output_on(self.psw,False)
        # self.psw=None
        self.initUI()
    def initUI(self):
        self.text = "初始化"
        # self.setGeometry(300, 300, 350, 300)
        # self.setWindowTitle('Drawing text')
        self.power_percent=0.
        self.isFcMode=True
        self.btn_text="切换到电解模式"
        # self.show()
    def updateVCP(self,voltage,current,power):
        if self.isFcMode:
            vcp="电池模式\n\n功率: {:.3f} W\n电压: {:.3f} V\n电流: {:.4f} A\n".format(power,voltage,current)
        else:
            hydrogen=abs(current/26.801/2.*23.8*20)
            vcp="电解模式\n\n产氢率: {:.3f} NL/h\n电压: {:.3f} V\n电流: {:.4f} A\n".format(hydrogen,voltage,current)
        self.text=vcp
        self.power_percent=power/max(self.max_power,0.1)
        self.update()
    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawText(event, qp)
        qp.end()
    def drawText(self, event, qp):
        qp.setPen(QtGui.QColor(0, 0, 0))
        qp.setFont(QtGui.QFont('微软雅黑', int(event.rect().height()*0.07)))
        shape=QtCore.QRect(int(event.rect().width()*0.5-event.rect().height()*0.45),int(event.rect().height()*0.05),int(event.rect().height()*0.9),int(event.rect().height()*0.9))
        # print(shape)
        qp.drawText(event.rect(), QtCore.Qt.AlignCenter, self.text)
        qp.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150),5,))
        qp.drawArc(shape,210*16,-240*16)
        # qp.setPen(QtGui.QPen(QtGui.QColor(200, 0, 0),10))  
        # gradient = QtGui.QConicalGradient(event.rect().width()*0.5-event.rect().height()*0.45, event.rect().height()*0.05, event.rect().height()*0.9)
        gradient = QtGui.QLinearGradient(QtCore.QPointF(event.rect().width()*0.5-event.rect().height()*0.45,event.rect().height()*0.5),QtCore.QPointF(event.rect().width()*0.5+event.rect().height()*0.45,event.rect().height()*0.5))
        # gradient.setColorAt(0, QtGui.QColor("#95BBFF"))
        # gradient.setColorAt(1, QtGui.QColor("#5C86FF"))
        gradient.setColorAt(0, QtGui.QColor(0,0,255))
        gradient.setColorAt(0.5, QtGui.QColor(0,255,0))
        gradient.setColorAt(1, QtGui.QColor(255,0,0))
        pen=QtGui.QPen()
        pen.setBrush(gradient)
        pen.setWidth(10) 
        pen.setCapStyle(QtCore.Qt.RoundCap)
        qp.setPen(pen)
        qp.drawArc(shape,210*16,-int(self.power_percent*240*16))
    def setMode(self):
        if not self.isFcMode:
            self.btn_text='切换到电解模式'
            p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>功率 (W)</font>''')
            p_power.setTitle('''<font color=red face='微软雅黑' size=6>功率</font>''')
            slider_current.text_current="负载电流 (A):"
            slider_current.l1.setText(slider_current.text_current)
            slider_current.qle_step.setText('50')
            slider_current.qle_time_step.setText('0.5')
            slider_current.l_limit.setText('测试起始电流 (A):')
            pws_output_on(self.psw,False)
        else:
            self.btn_text='切换到电池模式'
            p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>产氢率 (NL/h)</font>''')
            p_power.setTitle('''<font color=red face='微软雅黑' size=6>产氢率</font>''')
            set_load_current(0.)
            slider_current.s1.setValue(0)
            # rm=pyvisa.ResourceManager()
            # self.psw = rm.open_resource('ASRL3::INSTR')#串口
            slider_current.text_current="电源电压 (V):"
            slider_current.l1.setText(slider_current.text_current)
            slider_current.qle_step.setText('50')
            slider_current.qle_time_step.setText('1.0')
            slider_current.l_limit.setText('测试起始电压 (V):')
            pws_output_on(self.psw,True)
        self.isFcMode=not self.isFcMode
        setting.btn_mode.setText(self.btn_text)
def setStyle(element):
    element.setFont(QtGui.QFont('微软雅黑',18))
    element.setAlignment(QtCore.Qt.AlignCenter)
class SliderCurrent(QtGui.QWidget):
    def __init__(self,parent=None):
        super(SliderCurrent, self).__init__(parent)
        layout=QtGui.QVBoxLayout()
        self.text_current="负载电流 (A):"
        self.l1=QtGui.QLabel(self.text_current)
        setStyle(self.l1)
        layout.addWidget(self.l1)

        self.qle_current = QtGui.QLineEdit(self)
        setStyle(self.qle_current)
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_current.setText('0.0000')
        # self.qle.insert('0.0000')
        layout.addWidget(self.qle_current)

        #创建水平方向滑动条
        self.s1=QtGui.QSlider(QtCore.Qt.Horizontal)
        ##设置最小值
        self.s1.setMinimum(0)
        #设置最大值
        self.s1.setMaximum(300000)
        #步长
        self.s1.setSingleStep(100)
        self.s1.setPageStep(100)
        #设置当前值
        self.s1.setValue(0)
        #刻度位置，刻度下方
        self.s1.setTickPosition(QtGui.QSlider.TicksBelow)
        #设置刻度间距
        self.s1.setTickInterval(10000)
        layout.addWidget(self.s1)
        #设置连接信号槽函数
        self.s1.valueChanged.connect(self.valuechange)

        self.btn_current = QtGui.QPushButton('设置', self)
        self.btn_current.clicked.connect(self.set_current)
        font = QtGui.QFont()
        font.setFamily('微软雅黑')
        font.setBold(True)
        font.setPointSize(15)
        font.setWeight(75)
        self.btn_current.setFont(font)
        # self.btn.move(40, 80)
        layout.addWidget(self.btn_current)

        self.text_limit="测试起始电流 (A):"
        self.l_limit=QtGui.QLabel(self.text_limit)
        setStyle(self.l_limit)
        layout.addWidget(self.l_limit)

        self.qle_limit = QtGui.QLineEdit(self)
        setStyle(self.qle_limit)
        self.qle_limit.setText('0.0000')
        self.qle_limit.textChanged[str].connect(self.onChanged_limit)
        layout.addWidget(self.qle_limit)

        self.text_step="时间步数 :"
        self.l_step=QtGui.QLabel(self.text_step)
        setStyle(self.l_step)
        layout.addWidget(self.l_step)

        self.qle_step = QtGui.QLineEdit(self)
        setStyle(self.qle_step)
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_step.setText('50')
        # self.qle.insert('0.0000')
        layout.addWidget(self.qle_step)

        self.text_time_step="时间步长 (s):"
        self.l_time_step=QtGui.QLabel(self.text_time_step)
        setStyle(self.l_time_step)
        layout.addWidget(self.l_time_step)

        self.qle_time_step = QtGui.QLineEdit(self)
        setStyle(self.qle_time_step)
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_time_step.setText('0.5')
        # self.qle.insert('0.0000')
        layout.addWidget(self.qle_time_step)
        
        self.btn_iv = QtGui.QPushButton('测试IV曲线', self)
        # self.btn.move(40, 80)
        self.btn_iv.clicked.connect(self.test_iv)
        self.btn_iv.setFont(font)
        layout.addWidget(self.btn_iv)

        self.pbar = QtGui.QProgressBar(self)
        layout.addWidget(self.pbar)
        # self.pbar.setGeometry(30, 40, 200, 25)
        self.pbar.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(layout)
        # # self.counter=0
        # self.last=0
    def valuechange(self):
        #输出当前地刻度值，利用刻度值来调节字体大小
        # print('current slider value=%s'%self.s1.value())
        # size=self.s1.value()
        # self.l1.setFont(QFont('Arial',size))
        current = self.s1.value()/10000.
        self.text_current = "{:.4f}".format(current)
        self.qle_current.setText(self.text_current)
        # self.l1.setText(self.text_current)
        # if self.counter%10==0:
        # if current-self.last>0.01 or current-self.last<-0.01 :
        #     print(current)
        #     set_load_current(current)
    # def value_write(self,current):
    #     self.s1.setValue(int(current*10000))
    #     self.text_current = "负载电流: {:.4f} A".format(current)
    #     self.l1.setText(self.text_current)
    #     # self.counter=self.counter%10+1
    #     self.last = current
    def set_current(self):
        # current = self.s1.value()/10000.
        value = float(self.qle_current.text())
        self.s1.setValue(int(value*10000))
        if paintVCP.isFcMode:
            set_load_current(value)
        else:
            pws_set_voltage(paintVCP.psw,value)
    def test_iv_thread(self,step,time_step):
        # current_max = self.s1.value()/10000. 
        current_limit = float(self.qle_limit.text())
        current_max = float(self.qle_current.text())
        current_step = (current_max-current_limit)/step
        time_str=time.strftime("%Y-%m-%d_%H点%M分%S秒", time.localtime())
        f = open("./output/output_iv_"+time_str+".csv", "a")
        f.write("time,voltage,current,power,hydrogen,mode\n")
        data_i=np.empty(0)
        data_v=np.empty(0)
        data_p=np.empty(0)
        for i in range(step+1): 
            voltage,current,power=0,0,0
            hydrogen=0
            mode ="FC"
            if paintVCP.isFcMode:
                set_load_current(current_limit+current_step*i)
            else:
                pws_set_voltage(paintVCP.psw,current_limit+current_step*i)
            if i==0:
                time.sleep(2)
            time.sleep(time_step)
            # voltage = pws_read_voltage(paintVCP.psw)
            if paintVCP.isFcMode:
                voltage,current,power=read_vcp()
            else:          
                voltage = pws_read_voltage(paintVCP.psw)
                current = -pws_read_current(paintVCP.psw)
                power = voltage*current
                hydrogen=abs(current/26.801/2.*23.8*20)
                mode="EC"
            delta_time = time_step*i
            output="{:.3f},{:.3f},{:.4f},{:.3f},{:.3f},{}\n".format(delta_time,voltage,current,power,hydrogen,mode)
            f.write(output)
            data_i=np.append(data_i,current)
            data_v=np.append(data_v,voltage)
            data_p=np.append(data_p,power)
            p_iv.setRange(xRange=[min(data_i),max(data_i)],yRange=[min(data_v)*0.95,max(data_v)*1.05],padding=0)
            curve_iv.setData(data_v,x=data_i)
            curve_ip.setData(data_p,x=data_i)
            self.pbar.setValue(int(i*(100/step)))
        f.close()

    def test_iv(self):
        step=int(self.qle_step.text())
        time_step=float(self.qle_time_step.text())
        self.pbar.setValue(0)
        th2 = threading.Thread(target=self.test_iv_thread,args=(step,time_step))
        th2.start()
    def onChanged_limit(self):
        self.s1.setMinimum(int(float(self.qle_limit.text())*10000))
class Setting(QtGui.QWidget):
    def __init__(self,parent=None):
        super(Setting, self).__init__(parent)
        layout=QtGui.QVBoxLayout()
        self.btn_mode = QtGui.QPushButton('切换到电解模式',paintVCP)
        self.btn_mode.clicked[bool].connect(paintVCP.setMode)
        font = QtGui.QFont()
        font.setFamily('微软雅黑')
        font.setBold(True)
        font.setPointSize(15)
        font.setWeight(75)
        self.btn_mode.setFont(font)
        layout.addWidget(self.btn_mode)

        self.text_power="最大功率 (W):"
        self.l_power=QtGui.QLabel(self.text_power)
        self.l_power.setFont(QtGui.QFont('微软雅黑',18))
        self.l_power.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.l_power)

        self.qle_power = QtGui.QLineEdit(self)
        self.qle_power.setFont(QtGui.QFont('微软雅黑',18))
        self.qle_power.setAlignment(QtCore.Qt.AlignCenter)
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_power.setText('150.0')
        # self.qle.insert('0.0000')
        self.qle_power.textChanged[str].connect(self.onChanged_power)
        layout.addWidget(self.qle_power)

        self.text_rate="采样速率 (Hz):"
        self.l_rate=QtGui.QLabel(self.text_rate)
        self.l_rate.setFont(QtGui.QFont('微软雅黑',18))
        self.l_rate.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.l_rate)

        self.qle_rate = QtGui.QLineEdit(self)
        self.qle_rate.setFont(QtGui.QFont('微软雅黑',18))
        self.qle_rate.setAlignment(QtCore.Qt.AlignCenter)
        self.qle_rate.setText('50.0')
        self.qle_rate.textChanged[str].connect(self.onChanged_rate)
        layout.addWidget(self.qle_rate)     
        self.setLayout(layout)

    def onChanged_power(self, text):
        paintVCP.max_power = float(self.qle_power.text())
    def onChanged_rate(self, text):
        global rate
        rate = float(self.qle_rate.text())
class DynamicTest(QtGui.QWidget):
    def __init__(self,parent=None):
        super(DynamicTest, self).__init__(parent)
        self.start_index = -1
        layout=QtGui.QVBoxLayout()

        self.cb = QtGui.QCheckBox('往返测试', self)
        self.cb.setFont(QtGui.QFont('微软雅黑',15))
        self.cb.toggle()
        # self.cb.stateChanged.connect(self.changeTitle)
        layout.addWidget(self.cb)

        self.cb_reverse = QtGui.QCheckBox('反向测试', self)
        self.cb_reverse.setFont(QtGui.QFont('微软雅黑',15))
        self.cb_reverse.stateChanged.connect(self.changeTitle)
        layout.addWidget(self.cb_reverse)

        self.cb_modeswitch = QtGui.QCheckBox('模式切换', self)
        self.cb_modeswitch.setFont(QtGui.QFont('微软雅黑',15))
        self.cb_modeswitch.stateChanged.connect(self.changeTitle)
        layout.addWidget(self.cb_modeswitch)

        self.combo = QtGui.QComboBox(self)
        self.combo.addItem('稳定性测试')
        self.combo.addItem('对照测试')
        self.combo.addItem('连续测试')
        
        
        self.combo.setFont(QtGui.QFont('微软雅黑',13))
        layout.addWidget(self.combo)

        self.btn_iv = QtGui.QPushButton('生成测试序列', self)
        self.btn_iv.clicked.connect(self.create_test_data)
        self.btn_iv.setFont(QtGui.QFont('微软雅黑',15,75))
        layout.addWidget(self.btn_iv)

        self.text_vector="测试序列 :"
        self.l_vector=QtGui.QLabel(self.text_vector)
        setStyle(self.l_vector)
        layout.addWidget(self.l_vector)

        self.tw=QtGui.QTableWidget(101,3)
        self.tw.setHorizontalHeaderLabels(['t (s)','U (V)','I (A)'])
        self.tw.setColumnWidth(0,50)
        self.tw.setColumnWidth(1,50)
        self.tw.setColumnWidth(2,50)
        layout.addWidget(self.tw)

        self.btn_iv = QtGui.QPushButton('测试动态性能', self)
        self.btn_iv.clicked.connect(self.test_dynamic)
        self.btn_iv.setFont(QtGui.QFont('微软雅黑',15,75))
        layout.addWidget(self.btn_iv)

        self.pbar = QtGui.QProgressBar(self)
        layout.addWidget(self.pbar)
        # self.pbar.setGeometry(30, 40, 200, 25)
        self.pbar.setAlignment(QtCore.Qt.AlignCenter)

        self.setLayout(layout)
    def changeTitle(self,state):
        # if state==QtCore.Qt.Checked and not cb_reverse.isChecked():
        if self.cb_modeswitch.isChecked() and not self.cb_reverse.isChecked():
            slider_current.text_current="电源电压 (V):"
            slider_current.l1.setText(slider_current.text_current)
            slider_current.l_limit.setText('测试起始电流 (A):')
        elif self.cb_modeswitch.isChecked() and self.cb_reverse.isChecked():
            slider_current.text_current="负载电流 (A):"
            slider_current.l1.setText(slider_current.text_current)
            slider_current.l_limit.setText('测试起始电压 (V):')
        else:
            slider_current.text_current="负载电流 (A):"
            slider_current.l1.setText(slider_current.text_current)
            slider_current.l_limit.setText('测试起始电流 (A):')


    def test_tvi_thread(self):
        global times,data_voltage,data_current,data_power,data_hydrogen
        step = self.tw.rowCount()
        start_time = time.time()
        start_time_tostr=time.localtime()
        self.start_index = len(times)-1
        time_step=1e-4
        i = 0
        
        while i<step:
            delta_time = time.time()-start_time
            input_time = float(self.tw.item(i,0).text())
            if delta_time-input_time<-1e-3:
                time.sleep(time_step)
                continue
            else:
                # if paintVCP.isFcMode:
                #     set_load_current(float(self.tw.item(i,2).text()))
                # else:
                #     pws_set_voltage(paintVCP.psw,float(self.tw.item(i,1).text()))
                if self.tw.item(i,1).text()=='OFF':
                    pws_output_on(paintVCP.psw,False)
                    paintVCP.isFcMode = True
                else:
                    pws_output_on(paintVCP.psw,True)
                    paintVCP.isFcModes = False
                    pws_set_voltage(paintVCP.psw,float(self.tw.item(i,1).text()))
                # print(self.tw.item(i,2).text())
                set_load_current(float(self.tw.item(i,2).text()))
                time.sleep(time_step)
                i+=1
                self.pbar.setValue(int(i*(100/step)))
        time.sleep(1)
        time_str=time.strftime("%Y-%m-%d_%H点%M分%S秒", start_time_tostr)
        data_t = times[self.start_index:]
        data_v = data_voltage[self.start_index:]
        data_i = data_current[self.start_index:]
        data_p = data_power[self.start_index:]
        data_h = data_hydrogen[self.start_index:]
        mode = paintVCP.isFcMode
        f = open("./output/output_dynamic_"+time_str+".csv", "a")
        f.write("time,voltage,current,power,hydrogen,mode\n")
        for i in range(len(data_t)):
            output="{:.3f},{:.3f},{:.4f},{:.3f},{:.3f},{}\n".format(data_t[i],data_v[i],data_i[i],data_p[i],data_h[i],mode)
            f.write(output)
        f.close()
        self.start_index = -1
    def test_dynamic(self):
        self.pbar.setValue(0)
        th3 = threading.Thread(target=self.test_tvi_thread,args=())
        th3.start()
    def create_test_data(self):
        if not self.cb_reverse.isChecked():
            data_limit = float(slider_current.qle_limit.text())
            data_max = float(slider_current.qle_current.text())
        else:
            data_limit = float(slider_current.qle_current.text())
            data_max = float(slider_current.qle_limit.text())
        n_step = int(slider_current.qle_step.text())
        if paintVCP.isFcMode:
            if self.cb_modeswitch.isChecked() and not self.cb_reverse.isChecked():
                data_limit_type="i"
                data_max_type="v"
                voltage_limit=data_voltage[-1]
                voltage_max=data_max
                current_limit=0
                current_max=data_limit
            elif self.cb_modeswitch.isChecked() and self.cb_reverse.isChecked():
                data_limit_type="v"
                data_max_type="i"
                voltage_limit=data_voltage[-1]
                voltage_max=data_limit
                current_limit=0
                current_max=data_max
            else:
                data_limit_type="i"
                data_max_type="i"
                voltage_limit=data_voltage[-1]
                voltage_max=data_voltage[-1]
                current_limit=data_limit
                current_max=data_max
            voltage_step = (voltage_max-voltage_limit)/n_step
            current_step = (current_max-current_limit)/n_step
        else:
            data_limit_type="v"
            data_max_type="v"
        data_step = (data_max-data_limit)/n_step
        time_step = float(slider_current.qle_time_step.text())
        if self.combo.currentText()=='连续测试':
            if self.cb.isChecked():
                self.tw.setRowCount(2*n_step+1)
            else:
                self.tw.setRowCount(n_step+1)
        elif self.combo.currentText()=='稳定性测试':
            self.tw.setRowCount(2*n_step)
        elif self.combo.currentText()=='对照测试':
            if self.cb.isChecked():
                self.tw.setRowCount(4*n_step)
            else:
                self.tw.setRowCount(2*n_step)
        if self.combo.currentText()=='连续测试':
            for i in range(n_step+1):
                self.tw.setItem(i,0,QtGui.QTableWidgetItem("{:.3f}".format(i*time_step)))
                if data_limit_type=='v' and data_max_type=='i':
                    self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(voltage_max-i*voltage_step)))
                    self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
                elif data_limit_type=='i' and data_max_type=='v':
                    self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                    self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(current_max-i*current_step)))
                elif data_limit_type=='i' and data_max_type=='i':
                    self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                    self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_limit+i*data_step)))
                elif data_limit_type=='v' and data_max_type=='v':
                    self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_limit+i*data_step)))
                    self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
            if self.cb.isChecked():
                for i in range(n_step+1):
                    self.tw.setItem(n_step+1+i,0,QtGui.QTableWidgetItem("{:.3f}".format((n_step+1)*time_step+i*time_step)))
                    if data_limit_type=='v' and data_max_type=='i':
                        self.tw.setItem(n_step+1+i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(n_step+1+i,2,QtGui.QTableWidgetItem("{:.4f}".format(current_limit+i*current_step)))  
                    elif data_limit_type=='i' and data_max_type=='v':
                        self.tw.setItem(n_step+1+i,1,QtGui.QTableWidgetItem("{:.4f}".format(voltage_limit+i*voltage_step)))
                        self.tw.setItem(n_step+1+i,2,QtGui.QTableWidgetItem("0.0000"))
                    elif data_limit_type=='i' and data_max_type=='i':
                        self.tw.setItem(n_step+1+i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(n_step+1+i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_max-(i+1)*data_step)))
                    elif data_limit_type=='v' and data_max_type=='v':
                        self.tw.setItem(n_step+1+i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_max-(i+1)*data_step)))
                        self.tw.setItem(n_step+1+ii,2,QtGui.QTableWidgetItem("0.0000"))                    
        elif self.combo.currentText()=='稳定性测试':
            for i in range(2*n_step+1):
                self.tw.setItem(i,0,QtGui.QTableWidgetItem("{:.3f}".format(i*time_step)))
                if i%2==0:
                    if data_limit_type=='i':
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                    elif data_limit_type=='v':
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
                else:
                    if data_max_type=='i':
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                    elif data_max_type=='v':
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
        elif self.combo.currentText()=='对照测试':
            for i in range(2*n_step):
                self.tw.setItem(i,0,QtGui.QTableWidgetItem("{:.3f}".format(i*time_step)))
                if data_limit_type=='v' and data_max_type=='i':
                    if i%2==0:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
                    else:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(current_limit+(i+1)/2*current_step)))
                elif data_limit_type=='i' and data_max_type=='v':
                    if i%2==0:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                    else:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(voltage_limit+(i+1)/2*voltage_step)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
                elif data_limit_type=='i' and data_max_type=='i':
                    if i%2==0:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                    else:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("OFF"))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_limit+(i+1)/2*data_step)))
                elif data_limit_type=='v' and data_max_type=='v':
                    if i%2==0:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_limit)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
                    else:
                        self.tw.setItem(i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_limit+(i+1)/2*data_step)))
                        self.tw.setItem(i,2,QtGui.QTableWidgetItem("0.0000"))
            if self.cb.isChecked():
                for i in range(2*n_step):
                    self.tw.setItem(2*n_step+i,0,QtGui.QTableWidgetItem("{:.3f}".format(2*n_step*time_step+i*time_step)))
                    if data_limit_type=='i' and data_max_type=='v':
                        if i%2==1:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("0.0000"))
                        else:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("OFF"))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("{:.4f}".format(current_max-(i+1)/2*current_step)))
                    elif data_limit_type=='v' and data_max_type=='i':
                        if i%2==1:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("OFF"))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                        else:
                            self.tw.setItem(2*n_step+ii,1,QtGui.QTableWidgetItem("{:.4f}".format(voltage_max-(i+1)/2*voltage_step)))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("0.0000"))
                    elif data_limit_type=='i' and data_max_type=='i':
                        if i%2==1:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("OFF"))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                        else:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("OFF"))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("{:.4f}".format(data_max-(i+2)/2*data_step)))
                    elif data_limit_type=='v' and data_max_type=='v':
                        if i%2==1:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_max)))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("0.0000"))
                        else:
                            self.tw.setItem(2*n_step+i,1,QtGui.QTableWidgetItem("{:.4f}".format(data_max-(i+2)/2*data_step)))
                            self.tw.setItem(2*n_step+i,2,QtGui.QTableWidgetItem("0.0000"))
app = QtGui.QApplication(sys.argv)
w=SSOFC()
w.setWindowState(QtCore.Qt.WindowMaximized)
paintVCP=PaintVCP()
title = QtGui.QLabel('''<font color=black face='微软雅黑'  style="font-weight:bold;font-size:36px">可逆固体氧化物电池综合能源系统测试平台<font>''')
# title = QtGui.QLabel('''<div style=”font-size:200px”>我字体大小为20px</div> ''')
title.setAlignment(QtCore.Qt.AlignCenter)
setting = Setting()

# btn_mode.setCheckable(True)
# text = QtGui.QLineEdit('enter text')
# listw = QtGui.QListWidget()
# lcd_voltage=QtWidgets.QLCDNumber(7)
# lcd_current=QtWidgets.QLCDNumber(7)
# lcd_power=QtWidgets.QLCDNumber(7)
slider_current=SliderCurrent()
dynamic_test=DynamicTest()
p_voltage = pg.PlotWidget()
p_current = pg.PlotWidget()
p_power = pg.PlotWidget()
# p_iv_widget = pg.PlotWidget()
p_ivp=pg.GraphicsView()
p_tvi=pg.GraphicsView()
layout = QtGui.QGridLayout()
w.setLayout(layout)
layout.addWidget(title, 0, 0,1,4)   # button goes in upper-left
layout.addWidget(setting,1,0,1,1)
layout.addWidget(paintVCP,2,0,2,1)
layout.addWidget(slider_current, 1, 2, 3, 1)
layout.addWidget(p_ivp, 1, 3, 3, 1)
# layout.addWidget(lcd_voltage, 1, 0)   # button goes in upper-left
# layout.addWidget(lcd_current, 2, 0)   # text edit goes in middle-left
# layout.addWidget(lcd_power, 3, 0)  # list widget goes in bottom-left
layout.addWidget(p_power, 1, 1, 3, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(p_voltage, 4, 0, 3, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(p_current, 4, 1, 3, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(dynamic_test, 4, 2, 3, 1)
layout.addWidget(p_tvi, 4, 3, 3, 1)

data_voltage=np.empty(0)
data_voltage_psw=np.empty(0)
p_voltage.showGrid(x=True,y=True)
p_voltage.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电压 U (V)</font>''',color="#00FF00")
p_voltage.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 t (s)</font>''',color="#FFFF00")
p_voltage.setTitle('''<font color=red face='微软雅黑' size=6>电压</font>''')
curve_voltage=p_voltage.plot(pen='#00FF00')

data_current=np.empty(0)
data_current_psw=np.empty(0)
p_current.showGrid(x=True,y=True)
p_current.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电流 I (A)</font>''',color="#00FF00")
p_current.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 t (s)</font>''',color="#FFFF00")
p_current.setTitle('''<font color=red face='微软雅黑' size=6>电流</font>''')
curve_current=p_current.plot(pen='#00FF00')

data_power=np.empty(0)
data_hydrogen=np.empty(0)
p_power.showGrid(x=True,y=True)
p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>功率 P (W)</font>''',color="#00FF00")
p_power.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 t (s)</font>''',color="#FFFF00")
p_power.setTitle('''<font color=red face='微软雅黑' size=6>功率</font>''')
curve_power=p_power.plot(pen='#00FF00')

p_iv=pg.PlotItem()
p_iv.showGrid(x=True,y=True)
p_iv.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电压 U (V)</font>''',color="#00FF00")
p_iv.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>电流 I (A)</font>''',color="#FFFF00")
# p_iv.setTitle('''<font color=red face='微软雅黑' size=6>IVP曲线</font>''')
curve_iv=p_iv.plot(pen='#00FF00')
a_power = pg.AxisItem("right")
v_power = pg.ViewBox()

l = pg.GraphicsLayout()
# 设置视图中心小部件 为该布局
p_ivp.setCentralWidget(l)
# l.addItem(curve_power)
l.addItem(p_iv, row = 2, col = 3,  rowspan=1, colspan=1)
l.addItem(a_power, row = 2, col = 5,  rowspan=1, colspan=1)
l.scene().addItem(v_power)
a_power.linkToView(v_power)
v_voltage = p_iv.vb
v_power.setXLink(v_voltage)
# p_iv.getAxis("left").setLabel('电流', color='#FFFFFF')
a_power.setLabel(axis='right',text='''<font face='微软雅黑' size=6>功率 P (W)</font>''',color="#FF0000")
# v_power.setTitle('''<font color=red face='微软雅黑' size=6></font>''')
v_power.setGeometry(v_voltage.sceneBoundingRect())
# v_voltage.addItem(pg.PlotCurveItem(x, y1, pen='#FFFFFF'))
# a_power.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>电流 (A)</font>''')
curve_ip=pg.PlotCurveItem(pen='#FF0000')
v_power.addItem(curve_ip)



p_tv=pg.PlotItem()
p_tv.showGrid(x=True,y=True)
p_tv.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电压 U (V)</font>''',color="#00FF00")
p_tv.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 t (s)</font>''',color="#FFFF00")
# p_iv.setTitle('''<font color=red face='微软雅黑' size=6>IVP曲线</font>''')
curve_tv=p_tv.plot(pen='#00FF00')
a_ti = pg.AxisItem("right")
v_ti = pg.ViewBox()

l_tvi = pg.GraphicsLayout()
# 设置视图中心小部件 为该布局
p_tvi.setCentralWidget(l_tvi)
l_tvi.addItem(p_tv, row = 2, col = 3,  rowspan=1, colspan=1)
l_tvi.addItem(a_ti, row = 2, col = 5,  rowspan=1, colspan=1)
l_tvi.scene().addItem(v_ti)
a_ti.linkToView(v_ti)
v_tv = p_tv.vb
v_ti.setXLink(v_tv)
a_ti.setLabel(axis='right',text='''<font face='微软雅黑' size=6>电流 I (A)</font>''',color="#FF0000")
v_ti.setGeometry(v_voltage.sceneBoundingRect())
curve_ti=pg.PlotCurveItem(pen='#FF0000')
v_ti.addItem(curve_ti)

# font = QtGui.QFont()
# font.setPixelSize(20)
# p_voltage.getAxis("bottom").tickFont = font
# p_voltage.getAxis("left").tickFont = font
# def plotData(data):
#     curve.setData(data)
#     # p.setRange(xRange=[0,len(data)],yRange=[0,1],padding=0)
def serialProcess():
    global data_voltage,data_current,data_power,data_hydrogen,p_power
    if ser.isOpen():
        # print("open success")
        remote_switch(True)
        load_switch(True)
        # remote_switch(False)
        start_time=time.time()
        time_str=time.strftime("%Y-%m-%d_%H点%M分%S秒", time.localtime())
        f = open("./output/output_"+time_str+".csv", "a")
        f.write("time,voltage,current,power,hydrogen,mode\n")
        i=0
        global times
        global rate
        while ser.isOpen():
            # read vcp
            # if voltage==-1 and current==-1 and power==-1:
            #     continue
            voltage,current,power = 0,0,0
            mode=""
            hydrogen=0
            # voltage = pws_read_voltage(paintVCP.psw)
            if paintVCP.isFcMode:
                voltage,current,power=read_vcp()
                mode="FC"
            else:
                voltage = pws_read_voltage(paintVCP.psw)
                current = -pws_read_current(paintVCP.psw)
                power = voltage*current
                mode="EC"
                hydrogen=abs(current/26.801/2.*23.8*20)
            delta_time =time.time()-start_time
            times=np.append(times,delta_time)
            output="{:.3f},{:.3f},{:.4f},{:.3f},{:.3f},{}\n".format(delta_time,voltage,current,power,hydrogen,mode)
            f.write(output)
            paintVCP.updateVCP(voltage,current,power)
            # slider_current.value_write(current)
            # lcd_voltage.display("{:.3f}".format(voltage))
            # lcd_current.display("{:.4f}".format(current))
            # lcd_power.display("{:.3f}".format(power))
            # print("---------------")
            # print("time:%.3f"%delta_time)
            # print("voltage:%.3f"%voltage)
            # print("current:%.4f"%current)
            # print("power:%.3f"%power)
            # if i<=historyLength:
            #     # data[i]=voltage
            #     data=np.append(data,voltage)
            #     i+=1
            # else:
            #     data[:-1]=data[1:]
            #     data[i-1]=voltage
            data_voltage=np.append(data_voltage,voltage)
            p_voltage.setRange(xRange=[0,times[-1]],yRange=[min(data_voltage)*0.95-0.01,max(data_voltage)*1.05],padding=0)
            curve_voltage.setData(data_voltage,x=times)

            data_current=np.append(data_current,current)
            p_current.setRange(xRange=[0,times[-1]],yRange=[min(data_current)*0.95-0.01,max(data_current)*1.05],padding=0)
            curve_current.setData(data_current,x=times)

            if paintVCP.isFcMode:
                # p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>功率 P (W)</font>''')
                # p_power.setTitle('''<font color=red face='微软雅黑' size=6>功率</font>''')
                data_power=np.append(data_power,power)
                data_hydrogen=np.append(data_hydrogen,0)
                p_power.setRange(xRange=[0,times[-1]],yRange=[min(data_power)*0.95-0.01,max(data_power)*1.05],padding=0)
                curve_power.setData(data_power,x=times)
            else:
                # p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>产氢率 (NL/h)</font>''')
                # p_power.setTitle('''<font color=red face='微软雅黑' size=6>产氢率</font>''')
                data_power=np.append(data_power,0)
                hydrogen=current/26.801/2.*23.8*20
                data_hydrogen=np.append(data_hydrogen,hydrogen)
                p_power.setRange(xRange=[0,times[-1]],yRange=[min(data_hydrogen),max(data_hydrogen)],padding=0)
                curve_power.setData(data_hydrogen,x=times)
            if dynamic_test.start_index>=0:
                p_tv.setRange(xRange=[times[dynamic_test.start_index],times[-1]],yRange=[min(data_voltage[dynamic_test.start_index:])*0.95,max(data_voltage[dynamic_test.start_index:])*1.05],padding=0)
                curve_tv.setData(data_voltage[dynamic_test.start_index:],x=times[dynamic_test.start_index:])
                curve_ti.setData(data_current[dynamic_test.start_index:],x=times[dynamic_test.start_index:])
            # print(times[-1])
            time_step = 1./max(rate,1)
            time.sleep(time_step)
portx="COM6"
bps=9600
# timex=5
#串口执行到这已经打开 再用open命令会报错
ser = serial.Serial(portx, int(bps), timeout=1, parity=serial.PARITY_NONE,stopbits=1)
# set_load_current(0.3)
th1 = threading.Thread(target=serialProcess,args=())
th1.start()

# psw.baud_rate = 9600
# timer = pg.QtCore.QTimer()
# timer.timeout.connect(plotData,args=(data,)) # 定时刷新数据显示
# timer.start(500) # 多少ms调用一次
sys.exit(app.exec_())

            