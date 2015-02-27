__author__ = 'wanghuafeng'
#coding:utf-8
import os
import re
import time
import json
import codecs
import requests
from bs4 import BeautifulSoup

PATH = os.path.dirname(os.path.abspath(__file__))

class ZhiHu(object):
    topic_root_url = 'http://www.zhihu.com/topics'#话题广场根目录
    root_url = 'http://www.zhihu.com'#根目录

    def __init__(self):
        self.chosen_id_list = []
        self._load_cat_id()

    def _load_cat_id(self):
        '''读取本地文件中不以#号开头的id信息，保存到self.chosen_id_list中'''
        filename = os.path.join(PATH, 'cat_id_mapping.txt')
        with codecs.open(filename, encoding='utf-8') as f:
            for line in f.readlines():
                if not line.startswith('#'):
                    # print line.strip()
                    topic_id = line.strip().split('\t')[-1]
                    self.chosen_id_list.append(topic_id)
            print len(self.chosen_id_list)

    def log_record(self):
        '''生成log句柄，用于记录日志'''
        log_filename = time.strftime('%Y_%m_%d.log')
        log_file = os.path.join(PATH, 'log', log_filename)
        self.log = codecs.open(log_file, mode='a', encoding='utf-8')

    def gen_all_topic_url_list(self):
        '''解析根目录页面，获取所有话题url'''
        try:
            html = requests.get(self.topic_root_url).text
        except BaseException:
            print 'request time out...'
            try:
                html = requests.get(self.topic_root_url).text
            except BaseException:
                print 'request time out...'
                timeFormat = time.strftime('%Y_%m_%d_%H:%M:%S')
                self.log.write("%s--topic root url log timeed out\n"%timeFormat)
                return []
        soup = BeautifulSoup(html)
        url_str = soup.find('ul', class_="zm-topic-cat-main clearfix")
        url_li_list = url_str.find_all('li', attrs={'data-id':True})
        print url_li_list
        url_list = [(item.a.text, item['data-id']) for item in url_li_list]
        print url_list
        codecs.open('cat_id_mapping.txt', mode='wb', encoding='utf-8').writelines([('\t'.join(item) + '\n') for item in url_list])

    def get_cookie_param(self):
        '''获取cookie信息'''
        cookie = requests.get(self.topic_root_url).cookies.get('_xsrf')
        print 'cookie info: ', cookie
        return cookie

    def get_topic_id(self, cattopic_id):
        '''由cattopic_id获取topic_id，这里去zhihu默认的请求次数（3次），即每个cattopic_id对应60个topic_id(/topic/19553298)'''
        topic_url = 'http://www.zhihu.com/node/TopicsPlazzaListV2'
        total_topic_id_set = set()
        for offset_index in range(3):
            post_data = {
                'method':'next',
                'params':'{"topic_id":%s,"offset":%d,"hash_id":""}',
                '_xsrf':'9095d080aa27b6669de39a5a5eb9c439',
                }
            post_data['params'] = post_data['params'] % (cattopic_id, offset_index*20)
            # print post_data
            json_html = requests.post(topic_url, data=post_data).text
            json_data = json.loads(json_html)
            msg_list = json_data.get('msg')
            # print len(msg_list)
            topic_url_list = [BeautifulSoup(item).find('a')['href'] for item in msg_list]
            # print topic_url_list#/topic/19553298
            total_topic_id_set |= set(topic_url_list)
        print len(total_topic_id_set)
        return total_topic_id_set

    def write_all_topic_id(self):
        total_id_set = set()
        for cattopic_id in self.chosen_id_list:
            total_id_set |= self.get_topic_id(cattopic_id)
        print len(total_id_set)#1524据个人习惯过滤后，余22个标签的1014个topic_id
        codecs.open('all_topic_id.txt', mode='wb', encoding='utf-8').writelines([item+'\n' for item in total_id_set])
# if __name__ == "__main__":
    # zhihu = ZhiHu()
    # start_time = time.time()
    # # zhihu.gen_all_topic_url_list()
    # # zhihu.get_cookie_param()
    # # zhihu.get_topic_id('1027')
    # zhihu.write_all_topic_id()
    # print time.time() - start_time

#**************************解析topic_id所对应url*********************************

def get_question_list_from_topic_url(topic_url, max_vote_count):
    '''根据topic_url解析出该页面中vote_count大于1000的所有question_id'''
    question_list = []
    r = requests.get(topic_url, timeout=15)
    if r.status_code == 404:
        return []
    html = r.text
    soup = BeautifulSoup(html)

    #该url下所有的问题
    div_level_list = soup.find_all('div', class_='content')#该topic下的所有问题
    # print 'question_count of div_level_list:', len(div_level_list)
    for answer_div in div_level_list:
        #该topic下第一个问题的相关信息
        answer_id = answer_div.h2.a['href']
        answer_vote_count = answer_div.find('a', class_='zm-item-vote-count').text.strip()
        if ('K' in answer_vote_count) or (int(answer_vote_count) > max_vote_count):
            # print answer_id, answer_vote_count
            question_list.append(answer_id)
    # print 'question_list len:', len(question_list)
    return question_list
# url = 'http://www.zhihu.com/topic/19551147/top-answers?page=1'
# get_question_list_from_topic_url(url)

def get_question_by_topic_id(topic_id, max_vote_count=1000):
    '''根据topic_id解析出vote_count大于1000的question_id,并返回'''
    topic_url_pattern = 'http://www.zhihu.com{}/top-answers?page=%s'.format(topic_id.rstrip())
    topic_question_list = []
    for page_index in range(1, 51):
        topic_url = topic_url_pattern % page_index
        #返回当前页中满足要求的question_id
        one_page_question_list = get_question_list_from_topic_url(topic_url, max_vote_count)
        #若返回question_list为空，则停止翻页
        if not one_page_question_list:
            return topic_question_list
        topic_question_list.extend(one_page_question_list)
        # print topic_url, 'page_index:', page_index,
    # print 'topic_question_list len:', len(topic_question_list)
    return topic_question_list
# get_question_by_topic_id('/topic/19551147')

def _load_topic_ids():
    '''读取所有的topic_id信息'''
    filename = os.path.join(PATH, 'all_topic_id_1014.txt')
    return codecs.open(filename, encoding='utf-8').readlines()

def get_all_question_ids():
    '''读取本地文件中的topic_id并解析所有大于1000的question_id'''
    topic_id_list = _load_topic_ids()
    total_id_list_len = len(topic_id_list)
    # print 'total_id_list_len:', len(topic_id_list)
    all_question_id_list = []
    topic_index = 0
    for topic_id in topic_id_list:
        topic_index += 1
        print total_id_list_len, topic_index,
        topic_question_list = get_question_by_topic_id(topic_id)
        print len(topic_question_list)
        all_question_id_list.extend(topic_question_list)
    codecs.open('whole_question_id.txt', mode='wb', encoding='utf-8').writelines(set([item+'\n' for item in all_question_id_list]))
# get_all_question_ids()
#***********************humor answer************************************
def get_humor_answer_by_topic_id():
    max_vote_count_limit = 500
    topic_id_list = _load_topic_ids()
    total_id_list_len = len(topic_id_list)
    zhihu_root_url = 'http://www.zhihu.com'
    # print 'total_id_list_len:', len(topic_id_list)
    fileObj_write = codecs.open('humor_Q_A.txt', mode='ab', encoding='utf-8')
    answer_id_obj = codecs.open('humer_Q_A_answer_id.txt', mode='ab', encoding='utf-8')
    topic_index = 0

    #由topic_id解析出所有question_id,去重
    total_topic_question_set = set()
    for topic_id in topic_id_list:
        topic_index += 1
        print total_id_list_len, topic_index
        topic_question_list = get_question_by_topic_id(topic_id, max_vote_count=max_vote_count_limit)
        # print len(topic_question_list)
        total_topic_question_set |= set(topic_question_list)
    print 'total_topic_question_set len is:', len(total_topic_question_set )

    #遍历question_id，获取符合要求的answer，并将对应answer_id写入本地
    for question_id in total_topic_question_set:
        answer_list = []
        url = zhihu_root_url + question_id
        r = requests.get(url, timeout=15)
        html = r.text
        soup = BeautifulSoup(html)
        try:
            main_content = soup.find('div', class_='zu-main-content')
            # question_title = main_content.find('div', id='zh-question-title')
            answer_item_list = main_content.find_all('div', class_='zm-item-answer')
            for answer_item in answer_item_list:
                vote_count = answer_item.find('span', class_='count').text
                #若点赞数大于1000，则将answer_id写入本地
                if ('K' in vote_count) or (int(vote_count)>max_vote_count_limit):
                    question_title = main_content.find('div', id='zh-question-title')
                    answer_item_content = answer_item.find('div', class_='zm-item-rich-text')
                    answer_item_content_str = answer_item_content.text.strip()

                    if len(answer_item_content_str) < 100:
                        # print answer_item_content_str
                        answer_list.append(str(answer_item_content).decode('utf-8'))

                        #将该answer对应的id写入到写入到本地
                        data_aid = answer_item['data-aid'].strip()
                        answer_id_obj.write(data_aid + '\n')
                else:
                    continue
            if answer_list:
                Q_A_dic = {'Q':str(question_title).decode('utf-8'), 'A':''.join(answer_list)}
                json_data = json.dumps(Q_A_dic)
                fileObj_write.write(json_data + '\n')
        except Exception, e:
            print e,
            print url
    # print '*'*40
# get_humor_answer_by_topic_id()

#***********************************************************
def get_answer_id():
    '''抓取点赞数超过1000的回答的answer_id'''
    zhihu_root_url = 'http://www.zhihu.com'
    question_id_filename = os.path.join(PATH, 'question_ids.txt')
    answer_id_set = set()
    with codecs.open(question_id_filename, encoding='utf-8') as f:
        index = 0
        for line in f.readlines():
            index += 1
            question_id = line.rstrip()
            url = zhihu_root_url + question_id
            r = requests.get(url, timeout=15)
            html = r.text
            soup = BeautifulSoup(html)
            try:
                main_content = soup.find('div', class_='zu-main-content')
                answer_item_list = main_content.find_all('div', class_='zm-item-answer')
                for answer_item in answer_item_list:
                    vote_count = answer_item.find('span', class_='count').text
                    #若点赞数大于1000，则将answer_id写入本地
                    if ('K' in vote_count) or (int(vote_count)>1000):
                        answer_item_content = answer_item.find('div', class_='zm-item-rich-text')
                        data_aid = answer_item['data-aid'].strip()
                        answer_id_set.add(data_aid)
                        print index
                    else:
                        # print vote_count, data_aid
                        continue
            except:
                print url
    codecs.open('answer_ids.txt', mode='wb', encoding='utf-8').writelines([item+'\n' for item in answer_id_set])
# get_answer_id()
