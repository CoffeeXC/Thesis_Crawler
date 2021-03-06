# -*- coding: utf-8 -*-
import scrapy
import Crawler.items
import pymongo
import Crawler.spiders.zhms


class ZhmsContentSpider(scrapy.Spider):
    name = 'zhms_content'
    allowed_domains = ['zhms.cn']
    start_item_id = 1  # 爬虫开始爬取的项目号

    home_url = 'http://www.zhms.cn'
    itemLimit = 16 * Crawler.spiders.zhms.PAGELIMIT  # 定义爬取项目数
    itemCnt = start_item_id

    # 连接数据库
    client = pymongo.MongoClient("localhost", 27017)
    db = client.Thesis
    dbCateList = db.CateList
    dbCateContent = db.CateContent
    nowItem = dbCateList.find_one({"cateID": itemCnt})

    # 避免开始爬取的项目号对应项目不存在
    if nowItem:
        start_url = nowItem['cateUrl']
    else:
        start_url = "http://www.zhms.cn/cp/28/"

    print("\033[0;32m\t [ ------------ 爬虫程序启动成功 ------------ ] \033[0m")
    print("\n 爬取项目目标: " + str(itemLimit) + "\n\n")

    def start_requests(self):
        """ 构造爬虫初始请求 """
        return [
            scrapy.FormRequest(self.start_url, callback=self.cateInfo_parse)
        ]

    def cateInfo_parse(self, response):
        """ 爬取每个美食项目的介绍 """

        # 构造需要数据的 XPath 表达式
        cateNameRegx = '/html/body/div[4]/div[2]/div/h1/text()'
        cateStarRegx = '//i[@class="ico-star ico-star-ct"]'
        cateInfoRegx = '/html/body/div[4]/div[2]/h2//text()'
        image_urlsRegx = '/html/body/div[4]/div[2]/img/@src'
        cateMakeUrlsRegx = '/html/body/div[4]/div[3]/div[1]/div[2]/ul/li/a/@href'

        # 获取该页面所有的项目名字以及链接
        cateName = response.xpath(cateNameRegx).extract()
        cateStar = response.xpath(cateStarRegx).extract()
        cateInfo = response.xpath(cateInfoRegx).extract()
        image_urls = response.xpath(image_urlsRegx).extract()
        cateMakeUrls = response.xpath(cateMakeUrlsRegx).extract()

        # 构造 CateContent Item 实例
        CateContent = Crawler.items.CateContent()

        # 向 Item 实例中存储数据
        CateContent['cateID'] = self.itemCnt

        # 美食名字
        if cateName:
            CateContent['cateName'] = cateName[0]
        else:
            CateContent['cateName'] = "None"

        # 美食评星
        if cateStar:
            CateContent['cateStar'] = len(cateStar)
        else:
            CateContent['cateStar'] = -1

        # 美食介绍
        if cateInfo:
            CateContent['cateInfo'] = "".join(cateInfo)
        else:
            CateContent['cateInfo'] = "None"

        # 美食图片 URL
        if image_urls:
            CateContent['image_urls'] = image_urls[0].split('?', 1)[0]
        else:
            pass

        # 爬取第二级美食制作页面：若存在则爬取并传递数据，否则直接返回已获取的数据
        if cateMakeUrls:
            cateMakeUrl = self.home_url + cateMakeUrls[0]
            yield scrapy.Request(
                url=cateMakeUrl,
                meta={'item': CateContent},
                callback=self.cateMake_parse)
        else:
            yield CateContent
            # 获取下一个项目的链接并加入待爬取列表
            self.itemCnt += 1
            if self.itemCnt < self.itemLimit:
                nowItem = self.dbCateList.find_one({"cateID": self.itemCnt})
                isOver = self.dbCateContent.find_one({"cateID": self.itemCnt})
                while True:
                    if nowItem and not isOver:
                        break
                    elif isOver:
                        self.itemCnt += 1
                        nowItem = self.dbCateList.find_one({
                            "cateID": self.itemCnt
                        })
                        isOver = self.dbCateContent.find_one({
                            "cateID": self.itemCnt
                        })
                    else:
                        pass
                nextItemUrl = nowItem['cateUrl']
                # print("---------------------")
                # print(type(nextItemUrl))
                yield scrapy.Request(nextItemUrl, callback=self.cateInfo_parse)

        print("\n")

    def cateMake_parse(self, response):
        """ 爬取每个美食项目的制作教程 """

        # 构造需要数据的 XPath 表达式
        prepareTimeRegx = '/html/body/div[4]/div[2]/div[1]/div[1]/div/dl/dd[1]/span/text()'
        accomplishTimeRegx = '/html/body/div[4]/div[2]/div[1]/div[1]/div/dl/dd[2]/span/text()'
        mainMaterialsRegx = '//*[@id="mainMaterial"]/ul/li'
        othersMaterialsRegx = '/html/body/div[4]/div[2]/div[1]/div[3]/ul/li'
        makeStepsRegx = '/html/body/div[4]/div[2]/div[1]/div[4]/ul/li'

        # 获取该页面所有的项目名字以及链接
        prepareTime = response.xpath(prepareTimeRegx).extract()
        accomplishTime = response.xpath(accomplishTimeRegx).extract()
        mainMaterials = response.xpath(mainMaterialsRegx)
        othersMaterials = response.xpath(othersMaterialsRegx)
        makeSteps = response.xpath(makeStepsRegx)

        # 获取上一级传递的 Item 实例
        CateContent = response.meta['item']

        # 向 Item 实例中存储数据
        # 准备时间
        if prepareTime:
            CateContent['prepareTime'] = prepareTime[0]
        else:
            CateContent['prepareTime'] = "None"

        # 完成时间
        if accomplishTime:
            CateContent['accomplishTime'] = accomplishTime[0]
        else:
            CateContent['accomplishTime'] = "None"

        # 主要食材
        if mainMaterials:
            mainMaterial = ""
            for it in mainMaterials:
                s = it.xpath(".//text()").extract()
                if s:
                    mainMaterial += "".join(s) + "; "
                else:
                    if mainMaterial:
                        pass
                    else:
                        mainMaterial = "None"
                    break
            CateContent['mainMaterial'] = mainMaterial
        else:
            CateContent['mainMaterial'] = "None"

        # 辅料
        if othersMaterials:
            othersMaterial = ""
            for it in othersMaterials:
                s = it.xpath(".//text()").extract()
                if s:
                    othersMaterial += "".join(s) + "; "
                else:
                    if othersMaterial:
                        pass
                    else:
                        othersMaterial = "None"
                    break
            CateContent['othersMaterial'] = othersMaterial
        else:
            CateContent['othersMaterial'] = "None"

        # 制作步骤
        if makeSteps:
            makeStep = ""
            for it in makeSteps:
                s = it.xpath("./h2//text()").extract()
                if s:
                    makeStep += "".join(s)
                else:
                    if makeStep:
                        pass
                    else:
                        makeStep = "None"
                    break
                s = it.xpath("./h3//text()").extract()
                if s:
                    makeStep += "".join(s)
                else:
                    if makeStep:
                        pass
                    else:
                        makeStep = "None"
                    break
            CateContent['makeStep'] = makeStep.replace("第", "\n第")
        else:
            CateContent['makeStep'] = "None"

        print("\n")

        # 返回 Item 实例
        yield CateContent

        # 限定爬取 Item 数量，获取下一个爬取项目的 URL，构造 Request
        self.itemCnt += 1
        if self.itemCnt < self.itemLimit:
            nowItem = self.dbCateList.find_one({"cateID": self.itemCnt})
            isOver = self.dbCateContent.find_one({"cateID": self.itemCnt})
            while True:
                if nowItem and not isOver:
                    break
                elif isOver:
                    self.itemCnt += 1
                    nowItem = self.dbCateList.find_one({
                        "cateID": self.itemCnt
                    })
                    isOver = self.dbCateContent.find_one({
                        "cateID": self.itemCnt
                    })
                else:
                    pass
            nextItemUrl = nowItem['cateUrl']
            yield scrapy.Request(nextItemUrl, callback=self.cateInfo_parse)

    def parse(self, response):
        pass
