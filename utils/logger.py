import tkinter as tk
import os
import sys
import re
import shlex
import pytz
import uuid
import yaml
import logging
from croniter import croniter
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import threading
from threading import Thread
import time
import queue

 


def print_message(message):
    """打印消息到输出框"""
    #message_queue.put(message)
    if hasattr(print_message, 'message_queue'):
        print_message.message_queue.put(message)

'''
在Python中，使用Tkinter进行GUI编程时，
如果多个线程需要更新同一个界面，
应该避免直接从子线程更新UI，
因为Tkinter不是线程安全的。
正确的做法是使用线程安全的方式来更新UI，
比如使用queue.Queue来传递消息，然后在主线程中处理这些消息并更新UI。
'''
'''
    if hasattr(print_message, 'output_box'):
        #这句代码会导致卡死
        print_message.output_box.insert(tk.END, str(message) + '\n')
        print_message.output_box.see(tk.END)  # 自动滚动到最新内容
        if hasattr(print_message, 'root'):
            print_message.root.update()  # 更新UI
'''


if __name__ == '__main__':
    pass