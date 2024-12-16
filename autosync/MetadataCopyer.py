import os
import threading
import time
import queue
import shutil
from utils.shentools import *
from utils.logger import print_message

class MetadataCopyer:
    def __init__(self, source_folder, target_folder, allowed_extensions, num_threads=8):
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.metadata_extensions = allowed_extensions
        self.num_threads = num_threads
        self.copied_metadatas = 0
        self.existing_links = 0
        self.file_queue = queue.Queue()
        print_message("初始化元数据复制器...")
        print_message(f"源文件夹: {source_folder}")
        print_message(f"目标文件夹: {target_folder}")
        print_message(f"允许的扩展名: {allowed_extensions}")

    def copy_metadata(self, source, target_file, thread_name):
        try:
            if os.path.exists(target_file):
                source_timestamp = os.path.getmtime(source)
                target_timestamp = os.path.getmtime(target_file)
                if source_timestamp > target_timestamp:
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    shutil.copy2(source, target_file)
                    print_message(f"线程 {thread_name}: 更新元数据 {source} => {target_file}")
                    self.copied_metadatas += 1
                else:
                    print_message(f"线程 {thread_name}: 元数据已是最新，跳过: {target_file}")
                    self.existing_links += 1
            else:
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                shutil.copy2(source, target_file)
                print_message(f"线程 {thread_name}: 复制元数据 {source} => {target_file}")
                self.copied_metadatas += 1
        except Exception as e:
            print_message(f"错误: 元数据复制失败 - {source}")
            print_message(f"错误详情: {str(e)}")

    def start_to_copy_metadata(self, thread_name):
        while True:
            source_file = self.file_queue.get()
            if source_file is None:
                print_message(f"线程 {thread_name} 完成任务")
                break
            
            relative_path = os.path.relpath(source_file, self.source_folder)
            target_file = os.path.join(self.target_folder, relative_path)
            
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            self.copy_metadata(source_file, target_file, thread_name)
            self.file_queue.task_done()

    def get_source_files(self):
        print_message(f"开始扫描源文件夹: {self.source_folder}")
        file_count = 0
        for dp, dn, filenames in os.walk(self.source_folder):
            for f in filenames:
                source_file = os.path.join(dp, f)
                if source_file.endswith(self.metadata_extensions):
                    file_count += 1
                    yield source_file
        print_message(f"扫描完成，找到 {file_count} 个元数据文件")

    def run(self):
        start_time = time.time()
        print_message("开始更新元数据...")
        print_message(f"使用 {self.num_threads} 个线程进行处理")
        
        # 创建与源文件夹同名的目标文件夹
        source_name = os.path.basename(os.path.normpath(self.source_folder))
        new_target_folder = os.path.join(self.target_folder, source_name)
        os.makedirs(new_target_folder, exist_ok=True)
        self.target_folder = new_target_folder  # 更新目标文件夹路径
        print_message(f"创建目标文件夹: {new_target_folder}")
        
        threads = []
        for i in range(self.num_threads):
            thread_name = f"Thread-{i + 1}"
            thread = threading.Thread(target=self.start_to_copy_metadata, args=(thread_name,))
            threads.append(thread)
            thread.start()
            print_message(f"启动线程: {thread_name}")

        for source_file in self.get_source_files():
            self.file_queue.put(source_file)

        # 添加停止任务
        for i in range(self.num_threads):
            self.file_queue.put(None)

        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time
        
        message = (
            f"完成更新元数据\n"
            f"总耗时: {total_time:.2f} 秒\n"
            f"总处理元数据数: {self.copied_metadatas + self.existing_links}\n"
            f"新复制元数据数: {self.copied_metadatas}\n"
            f"跳过元数据数: {self.existing_links}"
        )
        print_message(message)
        return total_time, message
