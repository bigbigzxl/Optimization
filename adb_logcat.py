#!/usr/bin/env python
#coding:utf-8
import os
import sys
import Queue


import subprocess
import sys, time
import threading
import Queue


class myThread (threading.Thread):   #继承父类threading.Thread
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q #传过来的是地址，因此这里直接用q形参或者self.q结果都是一样的，能实现全局操作。
    def run(self):#把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        self.deal_data()

    def deal_data(self):

        cmd1 = "adb logcat *:E"
        process = subprocess.Popen(
            cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        while True:
            outline = process.stdout.readline()
            if outline == '' and process.poll() != None:
                print "break"
                break
            if outline != '' and "label:zxl" in outline:
                # sys.stdout.write(out)
                # sys.stdout.flush()
                # print outline
                if self.q.qsize() > 4096:
                    print "you deal data too slow, drop datas..."
                    continue

                self.q.put_nowait(outline)

current_imgNo = -1
current_boxIndex = -1
PROCESS = 0
def parse_save_file(line):
    global  current_boxIndex
    global  current_imgNo
    values = line.strip().split("=")[-1].split(",", 2)
    imgNo = int(values[0])
    boxIndex = int(values[1])

    path  = os.path.join(os.getcwd(), "box_int16_precise\\%d.txt"%imgNo)
    if current_imgNo != imgNo:
        with open(path, "w") as f:
            f.write(values[-1]+"\n")
        current_imgNo = imgNo
        current_boxIndex = boxIndex
        print "write Img%d Box%d"%(current_imgNo, current_boxIndex)
    else:
        if boxIndex - current_boxIndex == 1:
            with open(path, "a+") as f:
                f.write(values[-1]+"\n")
                # print values[-1]
            current_boxIndex = boxIndex
            print "write Img%d Box%d" % (current_imgNo, current_boxIndex)
        else:
            print "Img%d Box%d: boxIndex - current_boxIndex=%d Drop!!!"%(current_imgNo, current_boxIndex,boxIndex - current_boxIndex)


if __name__ == "__main__":
    GET_DATA = 0
    CHECK_FILE = 1

    if GET_DATA:
        q = Queue.Queue()
        thread1 = myThread(1, "Thread-1",q)
        thread1.start()

        while True:
            if q.qsize() > 0:
                line =  q.get_nowait()
                if line:
                    parse_save_file(line)

    if CHECK_FILE:
        folder_path = os.path.join(os.getcwd(), "box_int16_precise")
        file_names = os.listdir(folder_path)
        bitmap = [0 for i in range(3629)]
        for i, value in enumerate(bitmap):
            if str(i)+".txt" not in file_names:
                print i
