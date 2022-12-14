#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 23:22:32 2020

@author: mac
"""

from StevenTricks.dfi import findval
from StevenTricks.netGEN import randomheader
from StevenTricks.fileop import logfromfolder, picklesave
from StevenTricks.warren.conf import collection
from StevenTricks.warren.crawler.model.twse import Log
from os import path, remove, makedirs
from time import sleep
from random import randint
from traceback import format_exc
import sys
import datetime
import requests as re
import pandas as pd

warehousepath = r'/Users/stevenhsu/Library/Mobile Documents/com~apple~CloudDocs/warehouse/stock'


def sleepteller(mode=None):
    if mode == 'long':
        time = randint(600, 660)
    else:
        time = randint(20, 30)
    print('Be about to sleep {}'.format(str(time)))
    sleep(time)


if __name__ == "__main__":
    stocklog = Log(warehousepath)
    log = stocklog.findlog('source', 'log.pkl')
    errorlog = stocklog.findlog('source', 'errorlog.pkl')
    # 先看有沒有現有的log和errorlog
    log = stocklog.updatelog(log, collection)
    # 如果有就新增，沒有就自創一個
    if errorlog is None:
        errorlog = pd.DataFrame([])
    # errorlog可以直接創一個空的df
    log = log.replace({'succeed': 'wait'})
    # 在抓取之前要先把有抓過的紀錄都改為待抓'wait'
    log = logfromfolder(path.join(warehousepath, 'source'), fileinclude=['.pkl'], fileexclude=['log'], log=log, fillval='succeed')
    # 比對資料夾內的資料，依照現有存在的資料去比對比較準確，有可能上次抓完，中間有動到資料

    for ind, col in findval(log, 'wait'):
        crawlerdic = collection[col]
        crawlerdic['payload']['date'] = ind.date().strftime("%Y%m%d")
        datapath = path.join(warehousepath, 'source', col)
        print(ind, col)
        makedirs(datapath, exist_ok=True)

        try:
            res = re.post(url=crawlerdic['url'], headers=next(randomheader()), data=crawlerdic['payload'], timeout=None)
            print('sleep ...')
            sleepteller()
        except KeyboardInterrupt:
            print("KeyboardInterrupt ... content saving")
            stocklog.savelog(log, logtype='source', kind='log.pkl')
            stocklog.savelog(log, logtype='source', kind='errorlog.pkl')
            print("Log saved .")
            sys.exit()

        except Exception as e:
            print("Unknowned error")
            print("===============")
            print(format_exc())
            # 較詳細的錯誤訊息
            print("===============")
            print(e)
            # 較簡陋的錯誤訊息
            log.loc[log.index == ind, col] = 'request error'
            errordic = {'crawlerdic': crawlerdic,
                        'errormessage1': format_exc(),
                        'errormessage2': e,
                        'errormessage3': 'request failed'}
            errorlog.loc[ind, col] = [errordic]
            stocklog.savelog(log, logtype='source', kind='log.pkl')
            stocklog.savelog(log, logtype='source', kind='errorlog.pkl')
            sleepteller(mode='long')
            continue

        if res.status_code == re.codes.ok:
            # 只要result的結果是正確，就只剩下是友資料還是當天休市的差別
            data = res.json()
            print(data['stat'])
            print('------------------')
            if data['stat'] == 'OK':
                log.loc[log.index == ind, col] = 'succeed'
            else:
                # 例假日或颱風假
                log.loc[log.index == ind, col] = 'close'
                stocklog.savelog(log, logtype='source', kind='log.pkl')
                continue
        else:
            print("Unknowned error")
            print("===============")
            log.loc[log.index == ind, col] = 'result error'
            errordic = {'crawlerdic': crawlerdic,
                        'request': res,
                        'requeststatus': res.status_code,
                        'errormessage1': 'result error'}
            errorlog.loc[ind, col] = [errordic]
            stocklog.savelog(log, logtype='source', kind='log.pkl')
            stocklog.savelog(log, logtype='source', kind='errorlog.pkl')
            sleepteller(mode='long')
            continue

        data['crawlerdic'] = crawlerdic
        data['request'] = res
        picklesave(data=data, path=path.join(datapath, col+'_'+str(ind.date()))+'.pkl')

        # 把以月為頻率的資料要刪除之前的資料，留當月最新的就好，不用每天都留
        if crawlerdic['freq'] == 'M':
            daterange = pd.date_range(start=ind.strftime('%Y-%m-1'), end=ind-datetime.timedelta(days=1), freq='D', inclusive='left')
            for d in daterange:
                if path.exists(path.join(datapath, col+'_'+str(d))+'.pkl'):
                    remove(path.join(datapath, col+'_'+str(d))+'.pkl')

        stocklog.savelog(log, logtype='source', kind='log.pkl')
