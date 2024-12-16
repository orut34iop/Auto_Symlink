import os
import threading
import time
import queue
import sys
import shutil
from pathlib import Path
import urllib.parse
from utils.shentools import *
from utils.logger import print_message

class SymlinkCreator:
    def __init__(
        self,
        source_folder,
        target_folder,
        allowed_extensions,
        symlink_mode="symlink",
        symlink_size=20,
        cloud_type=None,
        cloud_root_path=None,
        cloud_url=None,
        num_threads=8,
    ):
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.allowed_extensions = allowed_extensions
        self.symlink_mode = symlink_mode
        self.symlink_size = symlink_size
        self.cloud_type = cloud_type
        self.cloud_root_path = cloud_root_path
        self.cloud_url = cloud_url
        self.num_threads = num_threads
        self.created_links = 0
        self.existing_links = 0
        self.symlink_name = symlink_name_dict.get(self.symlink_mode)
        self.file_queue = queue.Queue()
        print_message(f"初始化{self.symlink_name}创建器...")
        print_message(f"源文件夹: {source_folder}")
        print_message(f"目标文件夹: {target_folder}")
        print_message(f"允许的扩展名: {allowed_extensions}")

    def create_symlink(self, src, dst, thread_name):
        try:
            if os.path.exists(dst):
                self.existing_links += 1
                print_message(f"线程 {thread_name}: {self.symlink_name}已存在，跳过: {dst}")
                return
            file_size = os.path.getsize(src)
            if file_size <= self.symlink_size * 1024 * 1024:
                shutil.copy2(src, dst)
                print_message(f"线程 {thread_name}: 复制文件 {src} => {dst}")
            else:
                os.symlink(src, dst)
                print_message(f"线程 {thread_name}: 创建符号链接 {src} => {dst}")
            self.created_links += 1
        except Exception as e:
            print_message(f"错误: {self.symlink_name}创建失败 - {src}")
            print_message(f"错误详情: {str(e)}")

    def check_strm(self, strm_path):
        try:
            with open(strm_path, "r") as f:
                strm_link = f.read().strip()
            strm_link = urllib.parse.quote(strm_link)
            file_extension = os.path.splitext(strm_link)[1]
            strm_media_path = strm_path.replace(".txt", "").replace(".strm", file_extension)
            source_file = strm_media_path.replace(self.target_folder, self.source_folder)
            return os.path.exists(source_file)
        except Exception as e:
            print_message(f"检查strm文件失败: {strm_path}")
            print_message(f"错误详情: {str(e)}")
            return False

    def create_strm_file(
        self,
        source_dir: str,
        target_dir: str,
        source_file: str,
        cloud_type: str,
        cloud_root_path: str,
        cloud_url: str,
        thread_name: str,
    ):
        try:
            # 获取视频文件名和目录
            target_file = source_file.replace(source_dir, target_dir)
            video_name = Path(target_file).name
            # 获取视频目录
            dest_path = Path(target_file).parent

            if not dest_path.exists():
                os.makedirs(str(dest_path), exist_ok=True)
                print_message(f"创建目标目录: {dest_path}")

            # 构造.strm文件路径
            strm_path = os.path.join(
                dest_path, f"{os.path.splitext(video_name)[0]}.strm"
            )
            
            if os.path.exists(strm_path):
                if self.check_strm(strm_path):
                    self.existing_links += 1
                    print_message(f"线程 {thread_name}: strm文件已存在且有效，跳过: {strm_path}")
                    return
                else:
                    os.remove(strm_path)
                    print_message(f"发现无效strm文件，已删除: {strm_path}")
                    print_message(f"开始创建新的strm文件: {strm_path}")
            # 云盘模式
            if cloud_type:
                # 替换路径中的\为/
                target_file = source_file.replace("\\", "/")
                target_file = target_file.replace(cloud_root_path, "")
                # 对盘符之后的所有内容进行url转码
                target_file = urllib.parse.quote(target_file, safe="")
                
                if str(cloud_type) == "cd2":
                    # 将路径的开头盘符"/mnt/user/downloads"替换为"http://localhost:19798/static/http/localhost:19798/False/"
                    target_file = f"http://{cloud_url}/static/http/{cloud_url}/False/{target_file}"
                elif str(cloud_type) == "alist":
                    target_file = f"http://{cloud_url}/d/{target_file}"
                else:
                    print_message(f"错误: 不支持的云盘类型 {cloud_type}")
                    return

            # 写入.strm文件
            with open(strm_path, "w") as f:
                f.write(target_file)
            self.created_links += 1
            print_message(f"线程 {thread_name}: 创建strm文件 {source_file} => {strm_path}")
            
        except Exception as e:
            print_message(f"创建strm文件失败: {source_file}")
            print_message(f"错误详情: {str(e)}")

    def create_and_print_link(self, thread_name):
        while True:
            source_file = self.file_queue.get()
            if source_file is None:
                print_message(f"线程 {thread_name} 完成任务")
                break
            
            relative_path = os.path.relpath(source_file, self.source_folder)
            target_file = os.path.join(self.target_folder, relative_path)
            # 确保目标文件夹存在，如果不存在则创建
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            if self.symlink_mode == "symlink":
                self.create_symlink(source_file, target_file, thread_name)
            elif self.symlink_mode == "strm":
                self.create_strm_file(
                    self.source_folder,
                    self.target_folder,
                    source_file,
                    self.cloud_type,
                    self.cloud_root_path,
                    self.cloud_url,
                    thread_name,
                )
            else:
                print_message(f"错误: 不支持的链接模式 {self.symlink_mode}，程序即将退出")
                sys.exit(0)
            
            self.file_queue.task_done()

    def get_source_files(self):
        print_message(f"开始扫描源文件夹: {self.source_folder}")
        file_count = 0
        for dp, dn, filenames in os.walk(self.source_folder):
            for f in filenames:
                source_file = os.path.join(dp, f)
                if source_file.lower().endswith(self.allowed_extensions):
                    file_count += 1
                    yield source_file
        print_message(f"扫描完成，找到 {file_count} 个符合条件的文件")

    def run(self):
        start_time = time.time()
        print_message(f"开始更新{self.symlink_name}...")
        print_message(f"使用 {self.num_threads} 个线程进行处理")

        # 创建与源文件夹同名的目标文件夹
        source_name = os.path.basename(os.path.normpath(self.source_folder))
        new_target_folder = os.path.join(self.target_folder, source_name)
        os.makedirs(new_target_folder, exist_ok=True)
        # 更新目标文件夹路径
        self.target_folder = new_target_folder
        print_message(f"创建目标文件夹: {new_target_folder}")

        threads = []
        for i in range(self.num_threads):
            thread_name = f"Thread-{i + 1}"
            thread = threading.Thread(
                target=self.create_and_print_link, args=(thread_name,)
            )
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
            f"完成更新{self.symlink_name}\n"
            f"总耗时: {total_time:.2f} 秒\n"
            f"总处理{self.symlink_name}数: {self.created_links + self.existing_links}\n"
            f"新创建{self.symlink_name}数: {self.created_links}\n"
            f"跳过{self.symlink_name}数: {self.existing_links}"
        )
        print_message(message)
        return total_time, message
