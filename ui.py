import tkinter as tk
from tkinterdnd2 import TkinterDnD, DND_FILES
import os
import sys
import ctypes
import pyperclip
from tkinter import messagebox, ttk, filedialog
import yaml
from autosync.MetadataCopyer import MetadataCopyer
from autosync.SymlinkCreator import SymlinkCreator
from utils.logger import print_message
from threading import Thread
import time
import queue


def request_admin_privileges():
    """请求管理员权限"""
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    else:
        # 以管理员权限重新启动脚本
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return False

def validate_inputs():
    """验证所有输入是否为空"""
    validations = [
        (source_entry.get().strip(), "链接文件夹不能为空"),
        (target_entry.get().strip(), "目标文件夹不能为空"),
        (thread_spinbox.get().strip(), "同步线程数不能为空"),
        (soft_link_entry.get().strip(), "软链接后缀不能为空"),
        (meta_entry.get().strip(), "元数据后缀不能为空")
    ]
    
    for value, message in validations:
        if not value:
            messagebox.showwarning("验证失败", message)
            return False
    return True

def save_config():
    """保存配置到config.yaml文件"""
    if not validate_inputs():
        return False
        
    config = {
        'Settings': {
            'source_folder': source_entry.get().strip(),
            'target_folder': target_entry.get().strip(),
            'thread_count': thread_spinbox.get().strip(),
            'soft_link_extensions': soft_link_entry.get().strip(),
            'metadata_extensions': meta_entry.get().strip(),
            'path_list': output_text.get(1.0, tk.END).strip()  # 保存文本区域内容
        }
    }
    
    try:
        # 确保config目录存在
        os.makedirs(os.path.dirname('config/config.yaml'), exist_ok=True)
        with open('config/config.yaml', 'w', encoding='utf-8') as configfile:
            yaml.dump(config, configfile, allow_unicode=True, default_flow_style=False)
        print_message("配置已保存到config/config.yaml")
        return True
    except Exception as e:
        error_msg = f"保存配置文件时出错：{str(e)}"
        print_message(error_msg)
        messagebox.showerror("错误", error_msg)
        return False

def load_config():
    """从config.yaml文件加载配置"""
    if not os.path.exists('config/config.yaml'):
        return
        
    try:
        with open('config/config.yaml', 'r', encoding='utf-8') as configfile:
            config = yaml.safe_load(configfile)
            
        if config and 'Settings' in config:
            settings = config['Settings']
            source_entry.delete(0, tk.END)
            source_entry.insert(0, settings.get('source_folder', ''))
            
            target_entry.delete(0, tk.END)
            target_entry.insert(0, settings.get('target_folder', ''))
            
            thread_spinbox.delete(0, tk.END)
            thread_spinbox.insert(0, settings.get('thread_count', '5'))
            
            soft_link_entry.delete(0, tk.END)
            soft_link_entry.insert(0, settings.get('soft_link_extensions', 
                '.mkv;.iso;.ts;.mp4;.avi;.rmvb;.wmv;.m2ts;.mpg;.flv;.rm'))
            
            meta_entry.delete(0, tk.END)
            meta_entry.insert(0, settings.get('metadata_extensions',
                '.nfo;.jpg;.png;.svg;.ass;.srt;.sup'))
                
            # 加载文本区域内容
            output_text.delete(1.0, tk.END)
            path_list = settings.get('path_list', '')
            if path_list:
                output_text.insert(tk.END, path_list)
            print_message("配置已加载")
    except Exception as e:
        error_msg = f"加载配置文件时出错：{str(e)}"
        print_message(error_msg)
        #messagebox.showerror("错误", error_msg)

def on_sync_all():
    """一键全同步按钮点击事件"""
    if save_config():
        # 请求管理员权限
        if not request_admin_privileges():
            sys.exit()
        
        try:
            # 获取基本配置信息
            target_folder = target_entry.get().strip()
            thread_count = int(thread_spinbox.get().strip())
            metadata_extensions = tuple(ext.strip() for ext in meta_entry.get().strip().split(';'))
            soft_link_extensions = tuple(ext.strip() for ext in soft_link_entry.get().strip().split(';'))
            
            # 获取路径列表
            path_list = output_text.get(1.0, tk.END).strip().split('\n')
            if not path_list or not path_list[0]:
                print_message("路径列表为空")
                #messagebox.showwarning("提示", "路径列表为空")
                return
                
            total_time = 0
            total_copied = 0
            total_existing = 0
            
            # 处理每个源文件夹
            for source_path in path_list:
                if not source_path.strip():
                    continue
                    
                print_message(f"开始处理源文件夹: {source_path}")
                copyer = MetadataCopyer(
                    source_folder=source_path.strip(),
                    target_folder=target_folder,
                    allowed_extensions=metadata_extensions,
                    num_threads=thread_count
                )
                
                # 运行元数据复制
                time_taken, message = copyer.run()
                total_time += time_taken
                total_copied += copyer.copied_metadatas
                total_existing += copyer.existing_links
                print_message(message)
            
            # 显示总结信息
            summary = (
                f"元数据同步完成\n"
                f"总耗时: {total_time:.2f} 秒\n"
                f"总处理文件数: {total_copied + total_existing}\n"
                f"新复制文件数: {total_copied}\n"
                f"跳过文件数: {total_existing}"
            )
            print_message(summary)
            
            total_time = 0
            total_created_links = 0

            # 每个源文件夹创建符号链接
            for source_path in path_list:
                if not source_path.strip():
                    continue
                    
                print_message(f"开始创建符号链接: {source_path}")
                creater = SymlinkCreator(
                    source_folder=source_path.strip(),
                    target_folder=target_folder,
                    allowed_extensions=soft_link_extensions,
                    num_threads=thread_count
                )
                
                # 运行符号链接创建
                time_taken, message = creater.run()
                total_time += time_taken
                total_created_links += creater.created_links
                print_message(message)
            
            # 显示总结信息
            summary = (
                f"符号链接创建完成\n"
                f"总耗时: {total_time:.2f} 秒\n"
                f"总创建符号链接文件数: {total_created_links}\n"
            )
            print_message(summary)
            #messagebox.showinfo("同步完成", summary)

        except Exception as e:
            error_msg = f"同步过程中出错：{str(e)}"
            print_message(error_msg)
            #messagebox.showerror("错误", error_msg)

def export_to_clipboard():
    """导出内容到剪贴板，使用消息框提供操作反馈"""
    try:
        content = output_text.get(1.0, tk.END).strip()
        if content:
            pyperclip.copy(content)
            print_message("内容已复制到剪贴板")
            messagebox.showinfo("成功", "内容已复制到剪贴板")
        else:
            print_message("输出框为空，无法导出")
            messagebox.showwarning("提示", "输出框为空，无法导出")
    except Exception as e:
        error_msg = f"复制到剪贴板时出错：{str(e)}"
        print_message(error_msg)
        messagebox.showerror("错误", error_msg)

def clear_all():
    """清空所有输入和输出内容"""
    source_entry.delete(0, tk.END)
    output_text.delete(1.0, tk.END)
    print_message("已清空所有内容")

def browse_folder(entry):
    """浏览文件夹"""
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)
        print_message(f"已选择文件夹: {folder}")

def scan_string(input_string):
    """解析拖拽数据中的路径"""
    result = []
    i = 0
    while i < len(input_string):
        if input_string[i] == '{':
            i += 1
            start = i
            while i < len(input_string) and input_string[i] != '}':
                i += 1
            result.append(input_string[start:i])
            i += 1
        else:
            start = i
            while i < len(input_string) and input_string[i] != ' ':
                i += 1
            result.append(input_string[start:i])
        
        if i < len(input_string) and input_string[i] == ' ':
            i += 1
    
    return [path for path in result if path.strip()]

def get_existing_paths():
    """获取输出框中已存在的路径列表"""
    content = output_text.get(1.0, tk.END).strip()
    if content:
        return set(content.split('\n'))
    return set()

def on_source_drop(event):
    """处理源文件夹拖拽事件"""
    try:
        existing_paths = get_existing_paths()
        folder_paths = scan_string(event.data)
        new_paths = [path for path in folder_paths if path not in existing_paths]
        
        if not new_paths:
            print_message("所有拖入的路径都已存在，已自动忽略")
            messagebox.showinfo("提示", "所有拖入的路径都已存在，已自动忽略")
            return
            
        folder_names = [os.path.basename(folder) for folder in new_paths]
        
        current_text = source_entry.get()
        if current_text:
            current_text += "; "
        source_entry.delete(0, tk.END)
        source_entry.insert(tk.END, current_text + '; '.join(folder_names))
        
        current_output = output_text.get(1.0, tk.END).strip()
        if current_output:
            output_text.insert(tk.END, '\n' + '\n'.join(new_paths))
        else:
            output_text.insert(tk.END, '\n'.join(new_paths))
        
        print_message(f"已添加新路径: {', '.join(new_paths)}")
        
    except Exception as e:
        error_msg = f"处理拖拽数据时出错：{str(e)}"
        print_message(error_msg)
        messagebox.showerror("错误", error_msg)

def on_target_drop(event):
    """处理目标文件夹拖拽事件"""
    try:
        folder_paths = scan_string(event.data)
        if len(folder_paths) > 1:
            print_message("目标文件夹只能拖入单个文件夹")
            messagebox.showwarning("提示", "目标文件夹只能拖入单个文件夹")
            return
        
        if folder_paths:
            folder_path = folder_paths[0]
            if os.path.isdir(folder_path):
                target_entry.delete(0, tk.END)
                target_entry.insert(0, os.path.abspath(folder_path))
                print_message(f"已设置目标文件夹: {folder_path}")
            else:
                print_message("请拖入文件夹而不是文件")
                messagebox.showwarning("提示", "请拖入文件夹而不是文件")
        
    except Exception as e:
        error_msg = f"处理拖拽数据时出错：{str(e)}"
        print_message(error_msg)
        messagebox.showerror("错误", error_msg)


# 定义一个函数，用于在主线程中处理消息并更新UI
def process_messages(root, output_box, queue):

    if not queue.empty():
        message = queue.get()
        # 将消息添加到输出框
        output_box.insert(tk.END, message + '\n')
        # 自动滚动到最新内容
        output_box.see(tk.END)
        # 安排下一次更新
    root.after(100, process_messages, root, output_box, queue)

# 创建主窗口
root = TkinterDnD.Tk()
root.title("符号链接文件生成器")
root.geometry("800x1024")

# 创建主框架
frame = ttk.Frame(root, padding=10)
frame.pack(fill=tk.BOTH, expand=True)

# 使用说明
help_text = "使用说明: 将文件夹拖拽到输入框即可生成路径列表 (自动忽略重复路径)"
help_label = ttk.Label(frame, text=help_text, foreground="gray")
help_label.pack(fill=tk.X, pady=(0, 10))

# 主文本区域（显示路径）
text_frame = ttk.Frame(frame)
text_frame.pack(fill=tk.BOTH, expand=True)
output_text = tk.Text(text_frame, height=15)
output_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

# 链接文件夹区域
source_frame = ttk.Frame(frame)
source_frame.pack(fill=tk.X, pady=2)
ttk.Label(source_frame, text="链接文件夹").pack(side=tk.LEFT)
source_entry = ttk.Entry(source_frame)
source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
ttk.Button(source_frame, text="浏览", command=lambda: browse_folder(source_entry)).pack(side=tk.RIGHT)

# 目标文件夹区域
target_frame = ttk.Frame(frame)
target_frame.pack(fill=tk.X, pady=2)
ttk.Label(target_frame, text="目标文件夹").pack(side=tk.LEFT)
target_entry = ttk.Entry(target_frame)
target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
ttk.Button(target_frame, text="浏览", command=lambda: browse_folder(target_entry)).pack(side=tk.RIGHT)

# 同步线程数
thread_frame = ttk.Frame(frame)
thread_frame.pack(fill=tk.X, pady=2)
ttk.Label(thread_frame, text="同步线程数:").pack(side=tk.LEFT)
thread_spinbox = ttk.Spinbox(thread_frame, from_=1, to=32, width=10)
thread_spinbox.set(5)
thread_spinbox.pack(side=tk.LEFT, padx=5)

# 软链接后缀
soft_link_frame = ttk.Frame(frame)
soft_link_frame.pack(fill=tk.X, pady=2)
ttk.Label(soft_link_frame, text="软链接后缀:").pack(side=tk.LEFT)
soft_link_entry = ttk.Entry(soft_link_frame)
soft_link_entry.insert(0, ".mkv;.iso;.ts;.mp4;.avi;.rmvb;.wmv;.m2ts;.mpg;.flv;.rm")
soft_link_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
ttk.Label(soft_link_frame, text="以;隔开").pack(side=tk.RIGHT)

# 元数据后缀
meta_frame = ttk.Frame(frame)
meta_frame.pack(fill=tk.X, pady=2)
ttk.Label(meta_frame, text="元数据后缀:").pack(side=tk.LEFT)
meta_entry = ttk.Entry(meta_frame)
meta_entry.insert(0, ".nfo;.jpg;.png;.svg;.ass;.srt;.sup")
meta_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
ttk.Label(meta_frame, text="以;隔开").pack(side=tk.RIGHT)

# 开始同步区域
sync_frame = ttk.LabelFrame(frame, text="开始同步", padding=5)
sync_frame.pack(fill=tk.X)

# 按钮组
button_frame = ttk.Frame(sync_frame)
button_frame.pack(fill=tk.X, pady=5)

buttons = [
    ("一键全同步", on_sync_all),
    ("创建软链接", None),
    ("下载元数据", None),
    ("复制到剪贴板", export_to_clipboard),
    ("清空文件夹列表", clear_all)
]

for btn_text, cmd in buttons:
    btn = ttk.Button(button_frame, text=btn_text, command=cmd)
    btn.pack(side=tk.LEFT, padx=2)

# 输出框区域
output_frame = ttk.LabelFrame(frame, text="日志", padding=5)
output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
output_box = tk.Text(output_frame, height=64, wrap=tk.WORD)
output_box.pack(fill=tk.BOTH, expand=True)
scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=output_box.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
output_box.configure(yscrollcommand=scrollbar.set)

# 创建一个队列用于线程间通信
message_queue = queue.Queue()

# 设置输出框到print_message函数
print_message.message_queue = message_queue

# 绑定拖拽事件
source_entry.drop_target_register(DND_FILES)
source_entry.dnd_bind('<<Drop>>', on_source_drop)

target_entry.drop_target_register(DND_FILES)
target_entry.dnd_bind('<<Drop>>', on_target_drop)



# 启动主线程中的消息处理
process_messages(root, output_box, message_queue)


# 加载配置
load_config()

# 运行主循环
root.mainloop()
