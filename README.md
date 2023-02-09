## 2.1 wikiextractor

### 2.1.1 简介

基于维基百科的语料生成训练数据。

### 2.1.2 GitHub链接

[https://github.com/attardi/wikiextractor](https://github.com/attardi/wikiextractor)

### 2.1.3 安装环境

#### 2.1.3.1 Python环境

安装python环境，建议采用anaconda方式安装，版本3.7。

    conda create -n wikiextractor python=3.7

激活环境，

    conda activate wikiextractor

#### 2.1.3.2 拉取代码

    git clone https://github.com/attardi/wikiextractor.git

***注意**：*需要将项目中*./wikiextractor/extract.py*文件中的两行pdb相关的代码注释掉。

#### 2.1.3.3 安装依赖包

    pip install wikiextractor

### 2.1.4 下载原始语料文件

#### 2.1.4.1 链接

链接：[https://dumps.wikimedia.org/zhwiki](https://dumps.wikimedia.org/zhwiki)
若我们把 zhwiki 替换为 enwiki，就能找到英文语料，如果替换为 frwiki，就能找到法语语料，依次类推。
具体语言列表可参考，[**ISO 639-1语言列表**](https://baike.baidu.com/item/ISO%20639-1/8292914?fr=aladdin)

#### 2.1.4.2 下载原始语料

以英文为例，可下载如下文件，
[https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2](https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2)

### 2.1.5 执行命令

将下载的语料置于项目根目录下后执行下述命令，

```
python -m wikiextractor.WikiExtractor \
       -b 100M \
       --processes 4 \
       --json \
       -o data \
       下载的语料包.bz2
```


-o用来指定输出目录，--process 用来指定使用的进程数目（默认为 1），-b 选项用来控制单个生成文件的大小（默认为 1M，文件越大，包含的词条也越多），最后的参数为要处理的原始压缩语料文件名称。程序运行完成以后，在输出目录下面会生成多个子目录，每个目录下面有一些生成的文件。

| 参数    | 含义                   |
| ------- | ---------------------- |
| o       | 输出目录               |
| b       | 控制单个生成文件的大小 |
| process | 进程数                 |
| json    | 生成json格式           |

 