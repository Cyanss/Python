import os
import shutil

import pdfkit
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileWriter

path_wk = r'E:\wkhtmltox\Install\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf = path_wk)
htmlTemplate = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
    {content}
    </body>
    </html>
    """


def requestUrl(url):
    response = requests.get(url)
    return response.content


def savePdf(html, fileName):
    """
    把所有html文件保存到pdf文件
    :param fileName:
    :param html:  html内容
    :param file_name: pdf文件名
    :return:
    """
    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'cookie': [
            ('cookie-name1', 'cookie-value1'),
            ('cookie-name2', 'cookie-value2'),
        ],
        'outline-depth': 10,
    }
    print(">>>>>>>>: {}".format(fileName))
    pdfkit.from_string(html, fileName, configuration=config, options=options)


class AnalysisHtml(object):
    baseUrl = "http://python3-cookbook.readthedocs.io/zh_CN/latest/"
    bookName = ""
    chapterInfo = []

    def __init__(self, url=baseUrl):
        self.baseUrl = url
        self.__parseTitleAndUrl__()

    def __parseTitleAndUrl__(self):
        """
        解析全部章节的标题和Url
        :param html: 需要解析的网页内容
        :return: None
        """
        html = requestUrl(self.baseUrl)
        soup = BeautifulSoup(html,"html.parser")

        # 获取书名
        self.bookName = soup.find('div', class_='wy-side-nav-search').a.text.replace('\n', '').replace(' ', '')
        print("bookName: {}".format(self.bookName))
        menu = soup.find_all('div',class_='section')
        chapterList = menu[0].div.ul.find_all('li',class_='toctree-l1')
        for chapter in chapterList:
            # 获取一级标题和URL
            # 标题中含有'/'和'*'会保存失败
            info = {'title': chapter.a.text.replace('/', '').replace('*', ''),
                    'url': self.baseUrl + chapter.a.get('href'),
                    'child_chapters': []}
            # 获取二级标题和Url
            if chapter.ul is not None:
                childChapterList = chapter.ul.find_all('li')
                for child in childChapterList:
                    url = child.a.get('href')
                    # 如果在URL中存在'#',则此URL为页面内链接，不会跳转到其他页面所以不需要保存
                    if '#' not in url:
                        info['child_chapters'].append({
                            'title': child.a.text.replace('/','').replace('*',''),
                            'url': self.baseUrl + child.a.get('href'),
                        })
            self.chapterInfo.append(info)
        self.__parseHtmlToPdf__()

    def __parseHtmlToPdf__(self):
        """
        解析URL，获取html，保存成pdf文件
        :return: None
        """
        try:
            for chapter in self.chapterInfo:
                print('>>>>>>: {}'.format(chapter))
                title = chapter['title']
                url = chapter['url']
                # 文件夹不存在则创建（多级目录）
                dir_name = os.path.join(os.path.dirname(__file__), 'gen', title)
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                html = self.__getChildContent__(url)
                pdfPath = os.path.join(dir_name, title + '.pdf')
                savePdf(html, os.path.join(dir_name, title + '.pdf'))

                children = chapter['child_chapters']
                if children:
                    for child in children:
                        html = self.__getChildContent__(child['url'])
                        pdf_path = os.path.join(dir_name, child['title'] + '.pdf')
                        savePdf(html, pdf_path)

        except Exception as e:
            print(e)
        self.__mergePdf__()

    def __mergePdf__(self):
        """
        合并pd
        :return: None
        """
        pageNum = 0
        pdfOutput = PdfFileWriter()

        for pdf in self.chapterInfo:
            # 先合并一级目录的内容
            firstLevelTitle = pdf['title']
            dirName = os.path.join(os.path.dirname(__file__), 'gen', firstLevelTitle)
            pdfPath = os.path.join(dirName, firstLevelTitle + '.pdf')
            pdfInput = PdfFileReader(open(pdfPath, 'rb'))
            # 获取 pdf 共用多少页
            pageCount = pdfInput.getNumPages()
            for i in range(pageCount):
                pdfOutput.addPage(pdfInput.getPage(i))
            # 添加书签
            parentBookmark = pdfOutput.addBookmark(
                firstLevelTitle, pagenum=pageNum)
            # 页数增加
            pageNum += pageCount
            # 存在子章节
            if pdf['child_chapters']:
                for child in pdf['child_chapters']:
                    secondLevelTitle = child['title']
                    childPdfPath = os.path.join(dirName, secondLevelTitle + '.pdf')

                    childPdfInput = PdfFileReader(open(childPdfPath, 'rb'))
                    # 获取 pdf 共用多少页
                    childPageCount = childPdfInput.getNumPages()
                    for i in range(childPageCount):
                        pdfOutput.addPage(childPdfInput.getPage(i))
                    # 添加书签
                    pdfOutput.addBookmark(
                        secondLevelTitle, pagenum=pageNum, parent=parentBookmark)
                    # 增加页数
                    pageNum += childPageCount
        # 合并
        pdfOutput.write(open(self.bookName, 'wb'))

    @staticmethod
    def __getChildContent__(url):
        """
        解析URL，获取需要的html内容
        :param url: 目标网址
        :return: html
        """
        html = requestUrl(url)
        soup = BeautifulSoup(html, 'html.parser')
        content = soup.find('div', attrs={'itemprop': 'articleBody'})
        return htmlTemplate.format(content=content)

    @staticmethod
    def __deleteTempFile__():
        # 删除所有章节文件
        shutil.rmtree(os.path.join(os.path.dirname(__file__), 'gen'))


if __name__ == '__main__':
    AnalysisHtml()
    # AnalysisHtml.__deleteTempFile__()