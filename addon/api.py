
#
# class AudioDownloader(QObject):
#     timeout = 15
#     s = requests.Session()
#
#     def __init__(self, audios):
#         super().__init__()
#         self.SIG = AudioDownloaderSIG()
#         self.audios = audios
#         self.SIG.log.emit(f'待下载任务{audios}')
#
#     def _download(self, file_name, url):
#         try:
#             r = self.s.get(url, stream=True)
#             with open(f'{file_name}.mp3', 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=1024):
#                     if chunk:
#                         f.write(chunk)
#             self.SIG.log.emit(f'{file_name} 下载完成')
#         except Exception as e:
#             self.SIG.log.emit(f'下载{file_name}:{url}异常: {e}')
#         finally:
#             self.SIG.progress.emit()
#
#     @pyqtSlot()
#     def run(self):
#         self.SIG.totalTasks.emit(len(self.audios))
#         TP = ThreadPool(2)
#         for file_name, url in self.audios:
#             TP.add_task(self._download, file_name, url)
#         TP.wait_complete()
#         self.SIG.downloadFinished.emit()
