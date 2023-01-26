#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 23:22:32 2020

@author: mac
"""
from StevenTricks.dfi import findval
from StevenTricks.netGEN import randomheader
from StevenTricks.fileop import logfromfolder, picklesave, pickleload
from StevenTricks.warren.conf import collection, db_path, dailycollection
from StevenTricks.warren.twse import Log
from os import path, remove, makedirs
from time import sleep
from random import randint
from traceback import format_exc
import sys
import datetime
import requests as re
import pandas as pd
import datetime


def sleepteller(mode=None):
    if mode == 'long':
        time = randint(600, 660)
    else:
        time = randint(10, 30)
    print('Be about to sleep {}'.format(str(time)))
    sleep(time)


if __name__ == "__main__":
    stocklog = Log(db_path)
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
    log = logfromfolder(path.join(db_path, 'source'), fileinclude=['.pkl'], fileexclude=['log'], direxclude=['stocklist'], dirinclude=[], log=log, fillval='succeed')
    # 比對資料夾內的資料，依照現有存在的資料去比對比較準確，有可能上次抓完，中間有動到資料
    n=0
    for _ in dailycollection['stocklist']['modelis']:

        df = pd.read_html(dailycollection['stocklist']['url'].format(str(_)), encoding='cp950')
        sleepteller()
        df = pd.DataFrame(df[0])
        # read_html是返回list，所以要取出0
        # if n==3:
        #     break
        # else:
        #     n+=1
        #     continue
        # break
        if df.empty is True:
            # 代表什麼都沒返回
            print("stocktable No:{} ___empty crawled result".format(str(_)))
            continue

        df = df.reset_index(drop=True).reset_index()
        # 先弄出一列是連續數字出來
        tablename = [list(set(_)) for _ in df.values if len(set(_)) == 2]
        # 要找出一整列都是重複的，當作table name，因為剛剛已經用reset_index用出一整數列了，得出的重複值會長這樣[3,重複值]，所以如果是我們要找的重複值，最少會有兩個值，一個是數列，一個是重複值
        df = df.drop(["index"], errors="ignore", axis=1)
        # 把index先刪掉
        df.columns = df.loc[0]
        # 指定第一列為column
        df = df.drop(0)
        # 避免跟column重複，所以先刪掉
        df = df.drop(["Unnamed: 6"], errors="ignore", axis=1)
        # 把用不到的數列先刪掉，欄位清理

        # df.loc[:, "date"] = datetime.now().date()
        # 增加一列日期

        # 以下對特殊欄位進行特殊處理
        # if "指數代號及名稱" in df:
        #     df.loc[:, ["代號", "名稱"]] = df.loc[:, "指數代號及名稱"].str.split(" |　", expand=True, n=1).rename(
        #         columns={0: "代號", 1: "名稱"})
        # elif "有價證券代號及名稱" in df:
        #     df.loc[:, ["代號", "名稱"]] = df.loc[:, "有價證券代號及名稱"].str.split(" |　", expand=True, n=1).rename(
        #         columns={0: "代號", 1: "名稱"})

        # df = df.rename(columns=colname_dic)
        # 把處理好的欄位重新命名

        # if pk not in df:
        #     print("no primary key")
        #     print(_)
        #     print(pk)
        #     print(df.columns)
        #     continue
        # 以上檢查是否有變更primary key欄位的狀況

        # tablename
        if len(tablename) > 1:
            # 如果有兩種以上產品名的情況
            name_index = [(a, b) for a, b in zip(tablename, tablename[1:] + [[None]])]
        elif len(tablename) == 1:
            # 只有一種產品名的情況
            name_index = [(tablename[0], [None])]
        else:
            # 沒有產品名，就單獨一個dataframe，那就不用特別處理直接儲存就好
            table = "無細項分類的商品{}".format(str(_))
            # df.loc[:, "product"] = table
            datapath = path.join(db_path, 'source', 'stocklist', table, datetime.datetime.today().strftime(table+'_%Y-%m-%d.pkl'))

            picklesave(df, datapath)
            # dm.to_sql_ex(df=df, table=table, pk=pk)
            continue
            # a=pickleload(datapath)
        # 利用同一個row的重複值來判斷商品項目名稱，同時判斷儲存的方式
        # 對於有產品細項名稱的商品開始做以下特殊處理
        for nameindex in name_index:
            start = nameindex[0]
            end = nameindex[1]

            startname, startint = [_ for _ in start if isinstance(_, str) is True][0], [_ for _ in start if isinstance(_, str) is False][0]
            endint = [_ for _ in end if isinstance(_, str) is False][0]
            # 先抓出起始的值和尾端值然後用slice來做切割，把資料分段儲存進table

            if end[0] is None:
                df_sub = df[startint + 1:]
            else:
                df_sub = df[startint + 1:endint]
            # if startname in rename_dic:
            #     startname = rename_dic[startname]
            # df_sub.loc[:, "product"] = startname
            datapath = path.join(db_path, 'source', 'stocklist', startname, datetime.datetime.today().strftime(startname + '_%Y-%m-%d.pkl'))
            picklesave(df_sub, datapath)
            # dm.to_sql_ex(df=df_sub, table=startname, pk=pk)
            # a=pickleload(r'/Users/stevenhsu/Library/Mobile Documents/com~apple~CloudDocs/warehouse/stock/source/stocklist/受益證券-資產基礎證券/受益證券-資產基礎證券_2023-01-26.pkl')

    for ind, col in findval(log, 'wait'):
        crawlerdic = collection[col]
        crawlerdic['payload']['date'] = ind.date().strftime("%Y%m%d")
        datapath = path.join(db_path, 'source', col)
        print(ind, col)
        makedirs(datapath, exist_ok=True)

        try:
            res = re.post(url=crawlerdic['url'], headers=next(randomheader()), data=crawlerdic['payload'], timeout=(3,7))
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
