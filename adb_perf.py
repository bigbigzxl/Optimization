# coding=utf-8
import os, sys, time
import Queue
import threading
import subprocess

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.axes_grid1 import Grid
from mpl_toolkits.axes_grid.anchored_artists import AnchoredText


class myThread_produce (threading.Thread):
    """
    继承父类threading.Thread


    Attributes
    ----------
    exposure : queue
        Exposure in queue.

    Methods
    -------
    colorspace(c='rgb')
        Represent the photo in the given colorspace.
    gamma(n=1.0)
        Change the photo's gamma exposure.

    """

    def __init__(self, threadID, name, q_data, PRINT=False):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        #传过来的是地址，因此这里直接用q形参或者self.q结果都是一样的，能实现全局操作。
        self.q = q_data
        self.perf_data_detected = False
        self.PRINT = PRINT
        # self.first_time_IN = True

    def run(self):
        #把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        self.produce_data()

    def produce_data(self):
        """
        检查到数据是目标数据就简单清洗（去除换行符、去掉空格保持“value1，value2， ....”格式）；
        然后就推送到数据队列；
        注：为了尽可能少的时间处理数据，此时是没有检测合法性（比如数据是否有缺损）的；
        :return:
        """

        # reset adb log buffer.
        os.system("adb logcat -c")

        cmd1 = "adb logcat *:E"
        process = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


        while True:
            # block read
            outline = process.stdout.readline()

            if outline == '' and process.poll() != None:
                print ("break")
                break

            if outline != '' and "label@perf" in outline:

                if self.q.qsize() > MAX_QUEUE_SIZE:
                    print ("WARNNING!!! you deal data too slow, drop datas...")
                    continue

                #  we have 12 perf Items(include Item name).
                # "E:LOG:label@perf,1,2,3,4....11" --> "label@perf,1,2,3,4....11"
                label_value_string = outline.strip().split(":")[-1]
                # "label@perf,1,2,3,4....11" --> ["label@perf", "1", "2", ..., "11"]
                if len(label_value_string.split(",")) == 12:
                    # "label@perf,1,2,3,4....11" --> "1,2,3,4....11"
                    values_string = label_value_string.replace(" ", "").split(",", 1)[-1]
                    self.q.put_nowait(values_string)
                    if self.PRINT:
                        # sys.stdout.write(value_string)
                        # sys.stdout.flush()
                        print "(Queue.size = %-4d)push net string datas into Queue(q_data): "%self.q.qsize(), values_string
                else:
                    print "WARNNING!!! perf data line miss datas, so! drop it."


class myThread_consume (threading.Thread):
    """
    继承父类threading.Thread

    Attributes
    ----------
    exposure : queue
        Exposure in queue.

    Methods
    -------
    colorspace(c='rgb')
        Represent the photo in the given colorspace.
    gamma(n=1.0)
        Change the photo's gamma exposure.

    """

    def __init__(self, threadID, name, q_data, q_show, PRINT=False):
        threading.Thread.__init__(self)
        self.threadID  = threadID
        self.name      = name
        self.q_data    = q_data
        self.q_show    = q_show
        self.showDatas = []
        self.PRINT = PRINT
    def run(self):
        #把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        self.consume_data()

    def consume_data(self):
        """
        deal perf datas.
        :return: None.
        """
        while True:
            if  self.q_data.qsize() > 0:
                # 队列接收纯净的values_string数据："1,2,3,4......11"
                line =   self.q_data.get_nowait()
                if line:
                    self.SAVEorSHOW_datas(line)
                else:
                    print "IO ERROR: get no data from data_queue."
            else:
                time.sleep(0.1)

    def SAVEorSHOW_datas(self, line):

        # （检查）只接收纯净的values_string数据："1,2,3,4......11"
        values = line.split(",")
        if len(values) != len(ITEMS):
            print "WARNNING: The number of values does not equal the number of items, so DROP IT!"
            return


        if SAVE_FILE:
            path = DIR_PATH
            if os.path.exists(path):
                with open(path, "a+") as f:
                    f.write(line + "\n")
            else:
                print "ERROR: path=%s is not axisted."%path
                exit(0)
            return

        if SHOW:
            try:
                float_values = [float(x) for x in values]
                if  self.q_show.qsize() < MAX_QUEUE_SIZE:
                    self.q_show.put_nowait(float_values)
                    if self.PRINT:
                        print "(Queue.size = %-4d)push float datas into Queue(q_show): "%self.q_show.qsize(), float_values
                else:
                    print "produce too quick(for SHOW)! drop it."
            except Exception as e:
                print e
                print "WARNNING: There is some error in converting string values to float values, so drop it"


class myThread_monitor(threading.Thread):
    """
     继承父类threading.Thread

     Attributes
     ----------
     exposure : queue
         Exposure in queue.

     Methods
     -------
     colorspace(c='rgb')
         Represent the photo in the given colorspace.
     gamma(n=1.0)
         Change the photo's gamma exposure.

     """

    def __init__(self, threadID, name, q_show, MODE="muti-figure"):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name     = name

        # queue for  monitor.
        self.q_show   = q_show

        # single mode for time profile;
        # muti mode for hardware profile;
        self.mode     = MODE

        # Time
        self.CurrentSystime         = []
        self.averageSystime         = []
        self.CurrentPerftime        = []
        self.averagePerftime        = []

        # IPC
        self.CurrentInstruction     = []
        self.averageInstruction     = []
        self.CurrentCycle           = []
        self.averageCycle           = []
        self.CurrentIPC             = []
        self.averageIPC             = []

        # L1 cache Read
        self.Current_L1D_R_access   = []
        self.average_L1D_R_access   = []
        self.Current_L1D_R_misses   = []
        self.average_L1D_R_misses   = []
        self.Current_L1D_R_missRate = []
        self.average_L1D_R_missRate = []

        # L1 cache write
        self.Current_L1D_W_access   = []
        self.average_L1D_W_access   = []
        self.Current_L1D_W_misses   = []
        self.average_L1D_W_misses   = []
        self.Current_L1D_W_missRate = []
        self.average_L1D_W_missRate = []

    def run(self):
        if self.mode == "single-figure":
            self.single_mode()
        elif self.mode == "muti-figure":
            self.muti_mode()
        else:
            print "ERROR: monitor mode(%s) not support!"%self.mode
            exit(0)

    def single_mode(self):
       pass


    def muti_mode(self):
        self.init_1figure9axes()
        self.monitor_1figure9axes()

    def init_1figure9axes(self):
        """
        同时显示9张数据表：
            instructions， L1D_R_misses  ， L1D_W_misses  ,
            cycles      ,  L1D_R_access  ,  L1D_W_access  ,
            IPC         ,  L1D_R_missRate,  L1D_W_missRate
        :return:
        """

        # reset status.
        plt.close('all')

        # 解决中文乱码问题
        self.myfont = fm.FontProperties(fname="C:/Windows/Fonts/simkai.ttf", size=14)

        # 注：matplot里面所有中文字符都得是：u"中文"的raw格式；
        matplotlib.rcParams["axes.unicode_minus"] = False

        # figure 3x3
        self.fig = plt.figure(figsize=(8, 6), dpi=80)

        self.grid = Grid(self.fig, rect=111, nrows_ncols=(3, 3),
                               axes_pad=0.25, label_mode='L',)

        self.Instruction_ax    = self.grid[0]
        self.Cycle_ax          = self.grid[3]
        self.IPC_ax            = self.grid[6]

        self.L1D_R_misses_ax   = self.grid[1]
        self.L1D_R_access_ax   = self.grid[4]
        self.L1D_R_missRate_ax = self.grid[7]

        self.L1D_W_misses_ax   = self.grid[2]
        self.L1D_W_access_ax   = self.grid[5]
        self.L1D_W_missRate_ax = self.grid[8]

        # 竖轴
        self.grid[0].set_ylabel(u'分子', fontproperties=self.myfont, fontsize=12)
        self.grid[3].set_ylabel(u'分母', fontproperties=self.myfont, fontsize=12)
        self.grid[6].set_ylabel(u'除积', fontproperties=self.myfont, fontsize=12)

        # 横轴
        self.grid[6].set_xlabel(u'IPC(Instructions/cycles)'   , fontproperties=self.myfont, fontsize=12)
        self.grid[7].set_xlabel(u'cache(miss/Read=miss rate)' , fontproperties=self.myfont, fontsize=12)
        self.grid[8].set_xlabel(u'cache(Read/Write=miss rate)', fontproperties=self.myfont, fontsize=12)

        # figure1 4x1
        self.fig1 = plt.figure(figsize=(8, 6), dpi=80)
        self.grid1 = Grid(self.fig1, rect=111, nrows_ncols=(4, 1),
                                axes_pad=0.25, label_mode='L', )

        self.IPC_ax_1            = self.grid1[0]
        self.L1D_R_missRate_ax_1 = self.grid1[1]
        self.L1D_W_missRate_ax_1 = self.grid1[2]
        self.Time_ax_1           = self.grid1[3]

        self.grid1[0].set_ylabel(u'L1D_W_missRate', fontproperties=self.myfont, fontsize=12)
        self.grid1[1].set_ylabel(u'L1D_R_missRate', fontproperties=self.myfont, fontsize=12)
        self.grid1[2].set_ylabel(u'IPC',            fontproperties=self.myfont, fontsize=12)
        self.grid1[3].set_ylabel(u'time{sys/perf}', fontproperties=self.myfont, fontsize=12)

        # 紧致layout
        plt.tight_layout()

        # plt.legend(loc="upper left", prop=self.myfont, shadow=True)

    def monitor_1figure9axes(self):

        # 开启交互模式
        plt.ion()

        while True:
            if self.q_show.qsize() > 0:
                values = self.q_show.get()
                # print "(q_show size = %-4d)monitor get datas from Queue(q_show): "%self.q_show.qsize(), values
                self.plot_muti_Datas(values)
                plt.pause(0.001)
            else:
                plt.pause(0.2)

        # 关闭交互模式，否则上面跑完后就闪退了。
        plt.ioff()

        # 图形显示
        plt.show()

        return

    def plot_muti_Datas(self, list_datas):

        """
        update values and then flush the monitor.
        :param list_datas:
        :return:
        """
        ##########################updata showline's data.##############################################
        self.flush_all_datas(list_datas)


        ##########################show fig0##############################################
        self.monitor3x3_list = [  # IPC
                                [self.Instruction_ax   , self.CurrentInstruction    , self.averageInstruction    ],
                                [self.Cycle_ax         , self.CurrentCycle          , self.averageCycle          ],
                                [self.IPC_ax           , self.CurrentIPC            , self.averageIPC            ],
                                # L1_D_R
                                [self.L1D_R_misses_ax  , self.Current_L1D_R_misses  , self.average_L1D_R_misses  ],
                                [self.L1D_R_access_ax  , self.Current_L1D_R_access  , self.average_L1D_R_access  ],
                                [self.L1D_R_missRate_ax, self.Current_L1D_R_missRate, self.average_L1D_R_missRate],
                                # L1_D_W
                                [self.L1D_W_misses_ax  , self.Current_L1D_W_misses  , self.average_L1D_W_misses  ],
                                [self.L1D_W_access_ax  , self.Current_L1D_W_access  , self.average_L1D_W_access  ],
                                [self.L1D_W_missRate_ax, self.Current_L1D_W_missRate, self.average_L1D_W_missRate]
                            ]

        for ax0_cur1_avr2 in self.monitor3x3_list:
            self.plot_axe(ax0_cur1_avr2[0], ax0_cur1_avr2[1], ax0_cur1_avr2[2])
        # # clf是清除所有的axes,是上层的figure用的；
        # self.Instruction_ax.cla()
        # self.Instruction_ax.plot(self.CurrentInstruction,        "r--", linewidth=2.0)
        # self.Instruction_ax.plot(self.averageInstruction,         "g-", linewidth=2.0)
        #
        # self.Cycle_ax.cla()
        # self.Cycle_ax.plot(self.CurrentCycle,                    "r--", linewidth=2.0)
        # self.Cycle_ax.plot(self.averageCycle,                     "g-", linewidth=2.0)
        #
        # self.IPC_ax.cla()
        # self.IPC_ax.plot(self.CurrentIPC,                        "r--", linewidth=2.0)
        # self.IPC_ax.plot(self.averageIPC,                         "g-", linewidth=2.0)
        #
        # self.L1D_R_access_ax.cla()
        # self.L1D_R_access_ax.plot(self.Current_L1D_R_access,     "r--", linewidth=2.0)
        # self.L1D_R_access_ax.plot(self.average_L1D_R_access,      "g-", linewidth=2.0)
        #
        # self.L1D_R_misses_ax.cla()
        # self.L1D_R_misses_ax.plot(self.Current_L1D_R_misses,     "r--", linewidth=2.0)
        # self.L1D_R_misses_ax.plot(self.average_L1D_R_misses,      "g-", linewidth=2.0)
        #
        # self.L1D_R_missRate_ax.cla()
        # self.L1D_R_missRate_ax.plot(self.Current_L1D_R_missRate, "r--", linewidth=2.0)
        # self.L1D_R_missRate_ax.plot(self.average_L1D_R_missRate, "g-" , linewidth=2.0)
        #
        # self.L1D_W_access_ax.cla()
        # self.L1D_W_access_ax.plot(self.Current_L1D_W_access,     "r--", linewidth=2.0)
        # self.L1D_W_access_ax.plot(self.average_L1D_W_access,      "g-", linewidth=2.0)
        #
        # self.L1D_W_misses_ax.cla()
        # self.L1D_W_misses_ax.plot(self.Current_L1D_W_misses,     "r--", linewidth=2.0)
        # self.L1D_W_misses_ax.plot(self.average_L1D_W_misses,     "g-" , linewidth=2.0)
        #
        # self.L1D_W_missRate_ax.cla()
        # self.L1D_W_missRate_ax.plot(self.Current_L1D_W_missRate, "r--", linewidth=2.0)
        # self.L1D_W_missRate_ax.plot(self.average_L1D_W_missRate, "g-" , linewidth=2.0)



        # 刷新横轴纵轴labels
        self.grid[0].set_ylabel(u'分子\n(instruction, L1_D_R_miss, L1_W_R_miss)', fontproperties=self.myfont, fontsize=12, rotation=90)
        self.grid[3].set_ylabel(u'分母\n(cycle, L1_D_R, L1_W_R)',                 fontproperties=self.myfont, fontsize=12, rotation=90)
        self.grid[6].set_ylabel(u'除积\n\n',                                      fontproperties=self.myfont, fontsize=12, rotation=90)

        self.grid[6].set_xlabel(u'IPC=Instructions/cycles'       , fontproperties=self.myfont, fontsize=12)
        self.grid[7].set_xlabel(u'cache: miss/Read=miss rate(%)' , fontproperties=self.myfont, fontsize=12)
        self.grid[8].set_xlabel(u'cache: miss/Write=miss rate(%)', fontproperties=self.myfont, fontsize=12)


        ##########################show fig1##############################################
        self.monitor4x1_list = [
            [self.L1D_W_missRate_ax_1, self.Current_L1D_W_missRate, self.average_L1D_W_missRate],
            [self.L1D_R_missRate_ax_1, self.Current_L1D_R_missRate, self.average_L1D_R_missRate],
            [self.IPC_ax_1,            self.CurrentIPC,             self.averageIPC],
            # [self.Time_ax_1,           self.CurrentPerftime,        self.averagePerftime]
        ]

        for ax0_cur1_avr2 in self.monitor4x1_list:
            self.plot_axe(ax0_cur1_avr2[0], ax0_cur1_avr2[1], ax0_cur1_avr2[2])

        # special show for time part
        self.Time_ax_1.cla()
        self.Time_ax_1.plot(self.CurrentPerftime, "r--o", linewidth=2.0, label="Perf")
        self.Time_ax_1.plot(self.CurrentSystime,   "g-o", linewidth=2.0, label="Sys")
        plt.legend(loc="upper right", prop=self.myfont, shadow=True)
        at = AnchoredText("perf_avr:%.2f\nsys_avr :%.2f" % (np.mean(self.CurrentPerftime), np.mean(self.CurrentSystime)),
                          prop=dict(size=8), frameon=True, loc=2)
        at.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        self.Time_ax_1.add_artist(at)
        self.Time_ax_1.grid(True)

        self.grid1[0].set_ylabel(u'L1D_W_missRate', fontproperties=self.myfont, fontsize=12)
        self.grid1[1].set_ylabel(u'L1D_R_missRate', fontproperties=self.myfont, fontsize=12)
        self.grid1[2].set_ylabel(u'IPC', fontproperties=self.myfont, fontsize=12)
        self.grid1[3].set_ylabel(u'time{sys/perf}', fontproperties=self.myfont, fontsize=12)

    def plot_axe(self, ax, current_values, average_values):
        """give me a ax and two list datas, i can plot two list on the axe you give

            Parameters
            ----------
            ax : plt.figure.axe
                The axe you are going to draw.

            current_values : float list
                current new data list.

            average_values : Tfloat list
                current new average data list.

            Returns
            -------
            None


            Examples
            --------
            .. code:: python

                # Example usage of myfunction
                self.plot_axe(ax0_cur1_avr2[0], ax0_cur1_avr2[1], ax0_cur1_avr2[2])
            """
        ax.cla()
        ax.plot(current_values, "r--o", linewidth=2.0)
        ax.plot(average_values, "g-o" , linewidth=2.0)

        at = AnchoredText("cur:%.2f\navr:%.2f"%(current_values[-1], average_values[-1]),
                          prop=dict(size=8), frameon=True,
                          loc=2,
                          )
        at.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        ax.add_artist(at)
        ax.grid(True)

    def flush_all_datas(self, list_datas):
        self.CurrentSystime.append(list_datas[0])
        self.averageSystime.append(np.mean(self.CurrentSystime))

        self.CurrentPerftime.append(list_datas[1])
        self.averagePerftime.append(np.mean(self.CurrentPerftime))

        self.CurrentInstruction.append(list_datas[2])
        self.averageInstruction.append(np.mean(self.CurrentInstruction))

        self.CurrentCycle.append(list_datas[3])
        self.averageCycle.append(np.mean(self.CurrentCycle))

        self.CurrentIPC.append(list_datas[4])
        self.averageIPC.append(np.mean(self.CurrentIPC))

        # L1 cache Read
        self.Current_L1D_R_access.append(list_datas[5])
        self.average_L1D_R_access.append(np.mean(self.Current_L1D_R_access))

        self.Current_L1D_R_misses.append(list_datas[6])
        self.average_L1D_R_misses.append(np.mean(self.Current_L1D_R_misses))

        self.Current_L1D_R_missRate.append(list_datas[7])
        self.average_L1D_R_missRate.append(np.mean(self.Current_L1D_R_missRate))

        # L1 cache write
        self.Current_L1D_W_access.append(list_datas[8])
        self.average_L1D_W_access.append(np.mean(self.Current_L1D_W_access))

        self.Current_L1D_W_misses.append(list_datas[9])
        self.average_L1D_W_misses.append(np.mean(self.Current_L1D_W_misses))

        self.Current_L1D_W_missRate.append(list_datas[10])
        self.average_L1D_W_missRate.append(np.mean(self.Current_L1D_W_missRate))

if __name__ == "__main__":

    ###############################################################################
    # 配置区域：
    #       配置路径、运行模式等参数；
    ###############################################################################

    # shared by main thread.
    MAX_QUEUE_SIZE = 4096
    RUN            = 1
    TEST           = 0

    # shared by consume thread.
    DIR_PATH       = os.getcwd()
    SAVE_FILE      = 0
    SHOW           = 1

    # shared by monitor thread.
    ITEMS          = ["sysT(us)"    , "perfT(us)"   ,
             "instructions", "cycles(T)"   , "IPC(%)"           ,
             "L1D_R_access", "L1D_R_misses", "L1D_R_missRate(%)",
             "L1D_W_access", "L1D_W_misses", "L1D_W_missRate(%)"]


    ###############################################################################
    # 初始化数据队列：
    #   数据队列q_data: push进去的是纯数据的字符串，去尾巴去空格，其中逗号为分割符；
    #   显示队列q_show: push进去的是list数组，已转换成了float格式；
    ###############################################################################

    if (sys.version_info > (3, 0)):
        # python3
        q_data = Queue()
        q_show = Queue()
    else:
        # python2
        q_data = Queue.Queue()
        q_show = Queue.Queue()






    ###############################################################################
    # 单元测试区域：
    #       可分为produce、consume、monitor三个部分进行单元测试；
    ###############################################################################
    if TEST:
        # TEST pattern1： produce --> check.
        produce = myThread_produce(1, "Thread_produce", q_data=q_data, PRINT=False)
        produce.start()

        # TEST pattern2: consume --> check.
        consume = myThread_consume(2, "Thread_consume", q_data=q_data, q_show=q_show, PRINT=False)
        consume.start()

        # # TEST pattern3： matplot muti-figure
        monitor = myThread_monitor(3, "Thread_monitor", q_show=q_show)
        monitor.start()


        while True:
            time.sleep(10);






    ###############################################################################
    # 运行区域
    ###############################################################################
    if RUN:

        # 1、子线程1负责去采集、粗过滤数据到公共的q_data队列中；
        produce = myThread_produce(1, "Thread_produce", q_data=q_data)
        produce.start()

        # 2、子线程2来从公共q_data队列中把数据取出来做后续精细处理,然后扔到q_show队列中去；
        consume = myThread_consume(2, "Thread_consume", q_data=q_data, q_show=q_show)
        consume.start()

        # 3、子线程3负责显示数据；
        monitor = myThread_monitor(3, "show progress", q_show)
        monitor.start()

        while True:
            # 有三个公司(produce, consume, monitor)，广州市区十套房，就天天睡大觉！气不气！？
            time.sleep(1)