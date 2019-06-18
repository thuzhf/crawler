#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from contextlib import contextmanager
from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import queue
import sys
import time
from multiprocessor import MPRoutine

def fileexists(infile):
    if os.path.isfile(infile) and os.path.getsize(infile):
        return True
    return False

class Crawler:
    def __init__(self, timeout=10):
        # phantomjs_service_args = [
        #     '--proxy-type=http',
        #     '--proxy=127.0.0.1:10809',
        # ]
        self.timeout = timeout
        # self.driver = webdriver.PhantomJS(service_args=phantomjs_service_args)
        chrome_options = webdriver.ChromeOptions()
        if sys.platform == 'win32':
            chrome_path = r'C:\Program Files (x86)\Google\Chrome Beta\Application\chrome.exe'
            chromedriver_path = r'E:\chromedriver_win32\chromedriver.exe'
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--proxy-server=127.0.0.1:10809')
        else:
            chrome_path = ''
            chromedriver_path = 'chromedriver'
        chrome_options.binary_location = chrome_path
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chromedriver_path, options=chrome_options)
        self.driver.implicitly_wait(self.timeout)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.close()
    def close(self):
        # self.driver.close()
        self.driver.quit()
    @contextmanager
    def wait_for_page_load(self, old_element):
        yield
        WebDriverWait(self.driver, self.timeout).until(staleness_of(old_element))

def get_texts(url, xpath):
    with Crawler() as crawler:
        d = crawler.driver
        d.get(url)
        print(d.title)
        WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        elements = d.find_elements_by_xpath(xpath)
        print(len(elements))
        r = []
        for i, e in enumerate(elements):
            # r.append(e.get_attribute('href'))
            code = e.text
            name = e.find_element_by_xpath('following-sibling::*[1]').text
            r.append([code, name])
            if i % 100 == 0:
                print(i, code, name)
        return r

def prepare_res():
    #crawler = Crawler()
    #return crawler
    chrome_options = webdriver.ChromeOptions()
    # # chrome_options.add_argument('--proxy-server=127.0.0.1:10809')
    # chrome_options.binary_location = r'C:\Program Files (x86)\Google\Chrome Beta\Application\chrome.exe'
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def tmp_func(crawler, names, url, xpath, outfile):
    if not url:
        return
    try:
        driver = crawler.driver
    except:
        driver = crawler
    if fileexists(outfile):
        return
    retry_times = 1
    while True:
        try:
            driver.get(url)
            WebDriverWait(driver, 10 * retry_times).until(EC.visibility_of_element_located((By.XPATH, xpath)))
            elements = driver.find_elements_by_xpath(xpath)
            break
        except:
            print('will sleep {}s and retry: {}'.format(retry_times, url))
            time.sleep(retry_times)
            retry_times += 1
    r = []
    for e in elements:
        code = e.find_element_by_xpath('td[1]').text
        name = e.find_element_by_xpath('td[2]').text
        try:
            name = e.find_element_by_xpath('td[3]').text
        except:
            pass
        try:
            url = e.find_element_by_xpath('td[1]/a').get_attribute('href')
        except:
            url = ''
        r.append([code, name, url])
    with open(outfile, 'w') as f:
        for code, name, url in r:
            f.write('{}\t{}\t{}\n'.format(code, '{}-{}'.format(names, name), url))
    print('DONE: {}'.format(outfile))

def get_administrative_regions(num_workers=0):
    # references:
    # http://www.stats.gov.cn/tjsj/tjbz/tjyqhdmhcxhfdm/2018/index.html
    # http://www.mca.gov.cn/article/sj/xzqh/
    # http://xzqh.mca.gov.cn/map
    outdirs = ['国', '省', '市', '县', '乡']
    base_url = 'http://www.stats.gov.cn/tjsj/tjbz/tjyqhdmhcxhfdm/2018/index.html'
    xpaths = ['/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr/td/a',
        '/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[@class="citytr"]',
        '/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[@class="countytr" or @class="towntr"]',
        '/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[@class="towntr" or @class="villagetr"]',
        '/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[@class="villagetr"]']

    with MPRoutine(tmp_func, prepare_res, num_workers) as mprt:
        os.makedirs(outdirs[0], exist_ok=True)
        params = []
        outfile = os.path.join(outdirs[0], '中国.txt')
        if not fileexists(outfile):
            with Crawler() as crawler:
                d = crawler.driver
                d.get(base_url)
                print(d.title)
                WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.XPATH, xpaths[0])))
                elements = d.find_elements_by_xpath(xpaths[0])
                with open(outfile, 'w') as f:
                    for e in elements:
                        url = e.get_attribute('href')
                        code = os.path.basename(url).split('.')[0] + '0000000000'
                        names = e.text
                        f.write('{}\t{}\t{}\n'.format(code, names, url))
                        tmp_outfile = os.path.join(outdirs[1], names + '.txt')
                        params.append([names, url, xpaths[1], tmp_outfile])
        else:
            with open(outfile) as f:
                for line in f:
                    code, names, url = line.rstrip('\r\n').split('\t')
                    tmp_outfile = os.path.join(outdirs[1], names + '.txt')
                    params.append([names, url, xpaths[1], tmp_outfile])
        print(len(params))
        os.makedirs(outdirs[1], exist_ok=True)
        mprt.results(params)

        params = []
        for fname in next(os.walk(outdirs[1], followlinks=True))[2]:
            if fname.endswith('.txt'):
                fpath = os.path.join(outdirs[1], fname)
                # print(fpath)
                with open(fpath) as f:
                    for line in f:
                        code, names, url = line.strip('\r\n').split('\t')
                        if not url:
                            continue
                        outfile = os.path.join(outdirs[2], names + '.txt')
                        params.append([names, url, xpaths[2], outfile])
        print(len(params))
        os.makedirs(outdirs[2], exist_ok=True)
        mprt.results(params)

        params = []
        for fname in next(os.walk(outdirs[2], followlinks=True))[2]:
            if fname.endswith('.txt'):
                fpath = os.path.join(outdirs[2], fname)
                with open(fpath) as f:
                    for line in f:
                        code, names, url = line.strip('\r\n').split('\t')
                        if not url:
                            continue
                        outfile = os.path.join(outdirs[3], names + '.txt')
                        params.append([names, url, xpaths[3], outfile])
        print(len(params))
        os.makedirs(outdirs[3], exist_ok=True)
        mprt.results(params)

        params = []
        for fname in next(os.walk(outdirs[3], followlinks=True))[2]:
            if fname.endswith('.txt'):
                fpath = os.path.join(outdirs[3], fname)
                with open(fpath) as f:
                    for line in f:
                        code, names, url = line.strip('\r\n').split('\t')
                        if not url:
                            continue
                        outfile = os.path.join(outdirs[4], names + '.txt')
                        params.append([names, url, xpaths[4], outfile])
        print(len(params))
        os.makedirs(outdirs[4], exist_ok=True)
        mprt.results(params)

def main():
    x1 = ['https://auto.16888.com/', '/html/body/div[8]/div/div[1]/a[2]']
    x2 = ['https://ip.cn', '//*[@id="result"]/div/p[1]/code']
    x3 = ['http://car.bitauto.com/', '//*[@id="treeList"]/ul/li/ul/li/a/div/span']
    x4 = ['https://baike.baidu.com/item/%E7%87%83%E6%96%99/29734', '/html/body/div/div[2]/div/div[2]/table/tbody/tr/td[1]/div']
    x5 = ['http://www.stats.gov.cn/tjsj/tjbz/tjyqhdmhcxhfdm/2018/index.html',
        '/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr/td/a']
    x6 = ['http://www.mca.gov.cn/article/sj/xzqh/2019/201901-06/201904301706.html', '/html/body/div[1]/table/tbody/tr[@height="19" and @style="mso-height-source:userset;height:14.25pt"]/td[2]']
    # x7 = ['http://www.mca.gov.cn/article/sj/xzqh/2019/201901-06/201904301706.html', '//td[position()=2 and @class="xl7032454"]']

    if 0:
        r = get_texts(*x6)
        with open('xzqh.txt', 'w') as f:
            for x in r:
                f.write('{}\t{}\n'.format(x[0], x[1]))

    if 1:
        get_administrative_regions()
    if 0:
        urls = ['https://baidu.com', 'https://google.com', 'https://bilibili.com', 'https://douyu.com', 'https://huya.com', 'https://twitter.com', 'https://facebook.com']
        test(urls)

if __name__ == '__main__':
    main()
