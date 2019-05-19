## 单词查询 API 模块

## Development Guide
可在该模块下添加自定义查询API，继承 `misc.AbstractQueryAPI`确保API能和插件兼容
之后将你的API 添加到当前目录`__init.py` 中的 `registered_apis`
列表中以注册，并且查询返回结果必须满足如下
```
{
    'term': str,
    'definition': [str] 或 [ ],
    'phrase': [(str,str)] 或 [ ],
    'image': str 或 '',
    'sentence': [(str,str)] 或 [ ],
    'BrEPhonetic': str,
    'AmEPhonetic': str,
    'BrEPron': str,
    'AmEPron': str,
}
```
