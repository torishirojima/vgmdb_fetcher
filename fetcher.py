import os
import re
import json
import configparser
import requests
import tageditor
from bs4 import BeautifulSoup

config = {}

config_items = {
    'remote_album_url': {
        'type': str,
        'default': None
    },
    'local_album_src': {
        'type': str,
        'default': None
    },
    'lang': {
        'type': str,
        'default': 'en',
    },
    'fill': {
        'type': int,
        'default': 2
    },
    'select_tab': {
        'type': str,
        'default': None
    },
    'multiple_value': {
        'type': bool,
        'default': True
    },
    'output_path': {
        'type': str,
        'default': None
    }
}

# 读取配置文件
def read_config():
    cfg = configparser.ConfigParser()
    cfg.read('./config.cfg', encoding='utf-8')
    keys = config_items.keys()
    for key in keys:
        if cfg.has_option("settings", key):
            option_type = config_items[key]['type']
            value = cfg.get('settings', key)
            if value == 'None':
                config[key] = None
                continue
            if option_type == str:
                config[key] = cfg.get('settings', key)
            elif option_type == int:
                config[key] = cfg.getint('settings', key)
            elif option_type == bool:
                config[key] = cfg.getboolean('settings', key)
        else:
            config[key] = config_items[key]['default']


def list_find(l, e):
    try:
        return l.index(e)
    except:
        return -1

# 清洗数据
def clean_text(text):
    return text.replace('\n', '').replace('\r', '').strip(' / ').strip(', ').strip()

def strB2Q(ustring):
  """把windows文件名不允许的特殊字符半角转全角"""
  rstring = ""
  sp_pattern = '\/:*?"<>|' # 特殊字符
  reg_pattern = r'[\\/:*?"<>|]' # 特殊字符正则模式串
  if len(re.findall(reg_pattern, ustring)) <= 0: # 没匹配到直接返回原串
    return ustring
  for uchar in ustring:
    if uchar == '\\':  # 匹配到\则转为-
        rstring += '-'
        continue
    if sp_pattern.find(uchar) <= 0:
        rstring += uchar
        continue
    inside_code = ord(uchar)
    if inside_code < 0x0020 or inside_code > 0x7e:   # 不是半角字符就返回原来的字符
      rstring += uchar
    if inside_code == 0x0020: # 除了空格其他的全角半角的公式为:半角=全角-0xfee0
      inside_code = 0x3000
    else:
      inside_code += 0xfee0
    rstring += chr(inside_code)
  return rstring

# 请求获得专辑页面信息
def fetch_vgmdb():
    print('fetching '+config['remote_album_url']+' ...')
    html = requests.get(config['remote_album_url'])
    soup = BeautifulSoup(html.text, 'lxml')
    return soup

# 获取专辑信息
def get_album_info(soup):
    info = {}
    info['Title'] = clean_text(soup.select('div#innermain span.albumtitle[lang="' + config['lang'] + '"]')[0].text)
    smallfontDiv = soup.select("td#rightcolumn div.smallfont div")
    for div in smallfontDiv:
        labels = div.select('b.label')
        if len(labels) > 0 and labels[0].text == 'Category':
            info['Category'] = clean_text(div.get_text(strip=True).replace('Category', ''))
            break
    tr_list = soup.select('div#innermain table#album_infobit_large tr')
    for tr in tr_list:
        [label_dom, value_dom] = tr.find_all('td')
        key = ''
        value = ''
        if ('class' in tr.attrs) and (list_find(tr.attrs['class'], 'maincred') >= 0):
            value = []
            key = label_dom.find('span', attrs={'class':'label'}).text
            val_dom = value_dom.find_all('span', attrs={'lang':config['lang']})
            if val_dom is not None:
                for dom in val_dom:
                    value.append(clean_text(dom.text))
                    if config['multiple_value'] is not True:
                        break
            key = clean_text(key)
        else:
            key = clean_text(label_dom.text)
            value = clean_text(value_dom.text)
        info[key] = value
    return info


# 获取默认的tl_id
def get_default_tl_id(tlnav_items):
    tab = 'English' if config['lang'] == 'en' else 'Japanese'
    index = 0
    for (idx, item) in enumerate(tlnav_items):
        if item.text.find(tab) >= 0:
            index = idx
            break
    a = tlnav_items[index].find('a')
    return a.attrs['rel'][0]

# 获取专辑信息
def get_album_track_info(soup):
    info = {}
    tlnav_items = soup.select('div#innermain ul#tlnav li')
    tl_id = ''
    select_tab = config['select_tab']
    if len(tlnav_items) <= 0:
        return None
    if select_tab is None:
        tl_id = get_default_tl_id(tlnav_items)
    elif select_tab.find('tl') < 0:
        try:
            index = int(select_tab)
            items = tlnav_items[index].find('a').attrs['rel'][0]
            tl_id = items[0] if isinstance(items, list) else items
        except:
            tl_id = get_default_tl_id(tlnav_items)
    else:
        tl_id = select_tab
    if not tl_id:
        return None
    disc_span = soup.select('div#tracklist>span#' +tl_id+ '>span')
    table = soup.select('div#tracklist>span#' +tl_id+ '>table')
    disc_no = 1
    for span in disc_span:
        if(span.span is None and span.text.find('Disc') >= 0):
            disc_name = 'Disc '+str(disc_no)
            info[disc_name] = {}
            tracklist_dom = table[disc_no - 1]
            tracklist = tracklist_dom.find_all('tr', attrs={'class':'rolebit'})
            for track_dom in tracklist:
                td = track_dom.find_all('td')
                track_no = clean_text(track_dom.find('span', attrs={'class':'label'}).text)
                title = clean_text(td[1].text)
                info[disc_name][track_no] = title
            disc_no += 1
    return info

# 编辑音频标签
def tag_audio(album_info, track_info):
    total_disc = len(track_info.keys())
    for disc_info in track_info:
        disc_dir = os.path.join(config['local_album_src'], disc_info)
        if total_disc == 1 and not os.path.exists(disc_dir):
            disc_dir = config['local_album_src']
        disc_no = disc_info.split(' ')[-1]
        audio_list = os.listdir(disc_dir)
        for audio_name in audio_list:
            fmt = audio_name.split('.')[-1]
            path = os.path.join(disc_dir, audio_name)
            try:
                tagger = tageditor.tagger.File(path)
            except:
                continue
            track_no = tagger['track'][0].split('/')[0].zfill(config['fill']) # 获取音频文件预先填入的音轨号
            title = track_info[disc_info][track_no]
            tagger.add('title', title)
            if 'Title' in album_info:
                tagger.add('album', album_info['Title'])
            if "Label" in album_info:
                tagger.add('album_artist', album_info['Label'])
            elif "Publisher" in album_info:
                tagger.add('album_artist', album_info['Publisher'])
            elif "Composer" in album_info:
                tagger.add('album_artist', album_info['Composer'])
            elif "Vocals" in album_info:
                tagger.add('album_artist', album_info['Vocals'])
            elif "Arranger" in album_info:
                tagger.add('album_artist', album_info['Arranger'])
            if "Release Date" in album_info:
                tagger.add('date', clean_text(album_info['Release Date'].split(',')[-1]))
            if "Category" in album_info:
                tagger.add('genre', album_info['Category'])
            tagger.add('cd', str(disc_no) + '/' + str(total_disc))
            tagger.save()
            title = strB2Q(title)
            os.rename(path, os.path.join(disc_dir, disc_no + '.' + track_no + '.' + title + '.'+fmt))

def main():
    read_config()
    if config['lang'] != 'ja' and config['lang'] != 'en':
        config['lang'] = 'en'
    album_info = None
    track_info = None
    if config['remote_album_url'] is None:
        print('"remote_album_url" is not specified')
        return 
    if config['local_album_src'] is None:
        print('"local_album_src" is not specified')
    soup = None
    try:
        soup = fetch_vgmdb()
    except Exception as e:
        print('Fetch failed')
        print(e)
    try:
        album_info = get_album_info(soup)
        track_info = get_album_track_info(soup)
    except Exception as e:
        print('Parse failed')
        raise(e)
    if track_info is None or album_info is None:
        print('Parse failed')
    else:
        output_path = None
        if config['local_album_src'] is None:
            output_path = config['output_path'] if config['output_path'] is not None else './' + strB2Q(album_info['Title']) + '.json'
            print('"local_album_src" is not specified')
        else:
            # tag_audio(album_info, track_info)
            if config['output_path'] is not None:
                output_path = config['output_path']
            print("Successfully modified")
        if output_path is not None:
            album_info['track'] = track_info
            with open(output_path, 'w') as f:
                json.dump(album_info, f, indent=2)

if __name__ == '__main__':
    main()