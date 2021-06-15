import serial
import binascii
import time
import pyqtgraph as pg
import array
import numpy as np
import threading
from pyqtgraph.Qt import QtGui,QtCore,QtWidgets
import sys
busy=False
rate=5
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
    remote_switch(True)
    input_data='AA 00 2A '+hex_current+'00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
    query(ser,input_data)
    remote_switch(False)
class SSOFC(QtGui.QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()


    def initUI(self):
        # self.setGeometry(0, 0, 1000, 800)
        self.setWindowTitle(u'可逆固体氧化物电池综合能源系统测试平台')
        self.resize(1000,800)
        self.setWindowIcon(QtGui.QIcon('.\icon2.ico'))
        self.show()
    def closeEvent(self,event):
        ser.close()#关闭端口
        event.accept()

class PaintVCP(QtGui.QWidget):
    def __init__(self):
        super().__init__()
        self.max_power = 200.
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
            hydrogen=current/26.801/2.*23.8
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
        self.isFcMode=not self.isFcMode
        if self.isFcMode:
            self.btn_text='切换到电解模式'
            p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>功率 (W)</font>''')
            p_power.setTitle('''<font color=red face='微软雅黑' size=6>功率</font>''')
        else:
            self.btn_text='切换到电池模式'
            p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>产氢率 (NL/h)</font>''')
            p_power.setTitle('''<font color=red face='微软雅黑' size=6>产氢率</font>''')
        btn_mode.setText(self.btn_text)

class SliderCurrent(QtGui.QWidget):
    def __init__(self,parent=None):
        super(SliderCurrent, self).__init__(parent)
        layout=QtGui.QVBoxLayout()
        self.text_current="负载电流 (A):"
        self.l1=QtGui.QLabel(self.text_current)
        self.l1.setFont(QtGui.QFont('微软雅黑',18))
        self.l1.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.l1)

        self.qle_current = QtGui.QLineEdit(self)
        self.qle_current.setFont(QtGui.QFont('微软雅黑',18))
        self.qle_current.setAlignment(QtCore.Qt.AlignCenter)
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

        self.text_step="时间步数 :"
        self.l_step=QtGui.QLabel(self.text_step)
        self.l_step.setFont(QtGui.QFont('微软雅黑',18))
        self.l_step.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.l_step)

        self.qle_step = QtGui.QLineEdit(self)
        self.qle_step.setFont(QtGui.QFont('微软雅黑',18))
        self.qle_step.setAlignment(QtCore.Qt.AlignCenter)
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_step.setText('20')
        # self.qle.insert('0.0000')
        layout.addWidget(self.qle_step)

        self.text_time_step="时间步长 (s):"
        self.l_time_step=QtGui.QLabel(self.text_time_step)
        self.l_time_step.setFont(QtGui.QFont('微软雅黑',18))
        self.l_time_step.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.l_time_step)

        self.qle_time_step = QtGui.QLineEdit(self)
        self.qle_time_step.setFont(QtGui.QFont('微软雅黑',18))
        self.qle_time_step.setAlignment(QtCore.Qt.AlignCenter)
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
        current = float(self.qle_current.text())
        self.s1.setValue(int(current*10000))
        set_load_current(current)
    def test_iv_thread(self,step,time_step):
        current_max = self.s1.value()/10000. 
        current_step = current_max/step
        data_i=np.empty(0)
        data_v=np.empty(0)
        for i in range(step+1): 
            set_load_current(current_step*i)
            time.sleep(time_step)           
            voltage,current,power=read_vcp()
            data_i=np.append(data_i,current)
            data_v=np.append(data_v,voltage)
            p_iv.setRange(xRange=[min(data_i),max(data_i)],yRange=[min(data_v)*0.95,max(data_v)*1.05],padding=0)
            curve_iv.setData(data_v,x=data_i)
            self.pbar.setValue(int(i*(100/step)))
    def test_iv(self):
        step=int(self.qle_step.text())
        time_step=float(self.qle_time_step.text())
        self.pbar.setValue(0)
        th2 = threading.Thread(target=self.test_iv_thread,args=(step,time_step))
        th2.start()
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
        self.qle_power.setText('200.0')
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
        # self.qle.setPlaceholderText('输入负载电流值')
        self.qle_rate.setText('5.0')
        # self.qle.insert('0.0000')
        self.qle_rate.textChanged[str].connect(self.onChanged_rate)
        layout.addWidget(self.qle_rate)

        self.setLayout(layout)

    def onChanged_power(self, text):
        paintVCP.max_power = float(self.qle_power.text())
    def onChanged_rate(self, text):
        global rate
        rate = float(self.qle_rate.text())
app = QtGui.QApplication(sys.argv)
w=SSOFC()
w.setWindowState(QtCore.Qt.WindowMaximized)
paintVCP=PaintVCP()
title = QtGui.QLabel('''<font color=black face='微软雅黑'  style="font-weight:bold;font-size:36px">可逆固体氧化物电池综合能源系统测试平台<font>''')
# title = QtGui.QLabel('''<div style=”font-size:200px”>我字体大小为20px</div> ''')
title.setAlignment(QtCore.Qt.AlignCenter)
setting = Setting()

# btn_mode.setCheckable(True)
text = QtGui.QLineEdit('enter text')
listw = QtGui.QListWidget()
# lcd_voltage=QtWidgets.QLCDNumber(7)
# lcd_current=QtWidgets.QLCDNumber(7)
# lcd_power=QtWidgets.QLCDNumber(7)
slider_current=SliderCurrent()
p_voltage = pg.PlotWidget()
p_current = pg.PlotWidget()
p_power = pg.PlotWidget()
p_iv = pg.PlotWidget()
layout = QtGui.QGridLayout()
w.setLayout(layout)
layout.addWidget(title, 0, 0,1,3)   # button goes in upper-left
layout.addWidget(setting,1,0,1,1)
layout.addWidget(paintVCP,2,0,2,1)
layout.addWidget(slider_current, 1, 1, 3, 1)
layout.addWidget(p_iv, 1, 2, 3, 1)
# layout.addWidget(lcd_voltage, 1, 0)   # button goes in upper-left
# layout.addWidget(lcd_current, 2, 0)   # text edit goes in middle-left
# layout.addWidget(lcd_power, 3, 0)  # list widget goes in bottom-left
layout.addWidget(p_power, 4, 0, 3, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(p_voltage, 4, 1, 3, 1)  # plot goes on right side, spanning 3 rows
layout.addWidget(p_current, 4, 2, 3, 1)  # plot goes on right side, spanning 3 rows

data_voltage=np.empty(0)
p_voltage.showGrid(x=True,y=True)
p_voltage.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电压 (V)</font>''')
p_voltage.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 (s)</font>''')
p_voltage.setTitle('''<font color=red face='微软雅黑' size=6>电压</font>''')
curve_voltage=p_voltage.plot()

data_current=np.empty(0)
p_current.showGrid(x=True,y=True)
p_current.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电流 (A)</font>''')
p_current.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 (s)</font>''')
p_current.setTitle('''<font color=red face='微软雅黑' size=6>电流</font>''')
curve_current=p_current.plot()

data_power=np.empty(0)
data_hydrogen=np.empty(0)
p_power.showGrid(x=True,y=True)
p_power.setLabel(axis='left',text='''<font face='微软雅黑' size=6>功率 (W)</font>''')
p_power.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>时间 (s)</font>''')
p_power.setTitle('''<font color=red face='微软雅黑' size=6>功率</font>''')
curve_power=p_power.plot()

p_iv.showGrid(x=True,y=True)
p_iv.setLabel(axis='left',text='''<font face='微软雅黑' size=6>电压 (V)</font>''')
p_iv.setLabel(axis='bottom',text='''<font face='微软雅黑' size=6>电流 (A)</font>''')
p_iv.setTitle('''<font color=red face='微软雅黑' size=6>IV曲线</font>''')
curve_iv=p_iv.plot()
# font = QtGui.QFont()
# font.setPixelSize(20)
# p_voltage.getAxis("bottom").tickFont = font
# p_voltage.getAxis("left").tickFont = font
# def plotData(data):
#     curve.setData(data)
#     # p.setRange(xRange=[0,len(data)],yRange=[0,1],padding=0)
def serialProcess(data_voltage,data_current,data_power,data_hydrogen,p_power):
    if ser.isOpen():
        # print("open success")
        remote_switch(False)
        load_switch(True)
        start_time=time.time()
        f = open("D:\labview\电子负载\output.csv", "a")
        f.write("time,voltage,current,power\n")
        i=0
        times=np.array([])
        global rate
        while ser.isOpen():
            # read vcp
            voltage,current,power=read_vcp()
            # if voltage==-1 and current==-1 and power==-1:
            #     continue
            delta_time =time.time()-start_time
            times=np.append(times,delta_time)
            output="{:.3f},{:.3f},{:.4f},{:.3f}\n".format(delta_time,voltage,current,power)
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
                data_power=np.append(data_power,power)
                data_hydrogen=np.append(data_hydrogen,0)
                p_power.setRange(xRange=[0,times[-1]],yRange=[min(data_power)*0.95-0.01,max(data_power)*1.05],padding=0)
                curve_power.setData(data_power,x=times)
            else:
                data_power=np.append(data_power,0)
                hydrogen=current/26.801/2.*23.8
                data_hydrogen=np.append(data_hydrogen,hydrogen)
                p_power.setRange(xRange=[0,times[-1]],yRange=[min(data_hydrogen),max(data_hydrogen)],padding=0)
                curve_power.setData(data_hydrogen,x=times)
            # print(times[-1])
            time_step = 1./max(rate,1)
            time.sleep(time_step)
portx="COM6"
bps=9600
# timex=5
#串口执行到这已经打开 再用open命令会报错
ser = serial.Serial(portx, int(bps), timeout=1, parity=serial.PARITY_NONE,stopbits=1)
# set_load_current(0.3)
th1 = threading.Thread(target=serialProcess,args=(data_voltage,data_current,data_power,data_hydrogen,p_power))
th1.start()
# timer = pg.QtCore.QTimer()
# timer.timeout.connect(plotData,args=(data,)) # 定时刷新数据显示
# timer.start(500) # 多少ms调用一次
sys.exit(app.exec_())

            