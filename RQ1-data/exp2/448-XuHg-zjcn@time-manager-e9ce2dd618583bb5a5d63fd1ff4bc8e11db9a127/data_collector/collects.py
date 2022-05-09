#!/usr/bin/python
# -*- coding: utf-8 -*-
import signal
from commd_line.init_config import init_config
from data_collector.camera.mtcnn_face import MTCNNFace


def stop(signalnum, handler):
    global mtc
    print('stopping')
    mtc.stop()


signal.signal(signal.SIGINT, stop)


if __name__ == '__main__':
    conf = init_config()
    db_path = conf['init']['db_path']
    mtc = MTCNNFace(db_path=db_path)
    mtc.start()