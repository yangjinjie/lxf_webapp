#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ORM, Object-Relational Mapping，把关系数据库的表结构映射到对象上。

"""

import asyncio, logging
import aiomysql


def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建连接池,每个http请求都从连接池连接到数据库
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', '127.0.0.1'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


async def destory_pool():
    """
    # 销毁连接池
    :return:
    """
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()


async def select(sql, args, size=None):
    """
    # select语句
    :param sql:
    :param args:
    :param size:
    :return:
    """
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs


async def execute(sql, args, autocommit=True):
    """
    # insert,update,deleta语句
    :param sql:
    :param args:
    :param autocommit:
    :return:
    """
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


def create_args_string(num):
    l = []
    for n in range(num):
        l.append('?')
    return ', '.join(l)


class Field(object):
    """
    定义Field类，负责保存(数据库)表的字段名和字段类型
    """
    def __init__(self, name, colunm_type, primary_key, default):
        self.name = name
        self.colunm_type = colunm_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s, %s>' % (self.__class__.__name__, self.colunm_type, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):
    """
    调用__init__方法前会调用__new__方法
    cls 当前准备创建的类的对象  name 类的名字 该类的父类  attrs 类的属性集合
    name  -> User
    bases -> (<class 'orm.Model'>,)
    attrs -> {'__table__': 'users', 'image': <orm.StringField object at 0x10c381860>, 'admin': <orm.BooleanField object at 0x10c3817f0>, '__module__': 'models', 'created_at': <orm.FloatField object at 0x10c381898>, 'id': <orm.StringField object at 0x10c381c18>, '__qualname__': 'User', 'passwd': <orm.StringField object at 0x10c381668>, 'email': <orm.StringField object at 0x10c381710>, 'name': <orm.StringField object at 0x10c381780>}
    """
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 如果没设置__table__属性，tableameN 就定义为类名
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = {}
        fields = []
        primarykey = None
        # 遍历 attrs 字典, 如果值是 Field 类型, 则加入到mappings字典
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                # 把键值对存入mapping字典中
                mappings[k] = v
                if v.primary_key:
                    # id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
                    # primary_key=True 则执行下面操作,如果primarykey已经定义过了,说明主键重复
                    #找到主键
                    if primarykey:
                        raise Exception('Duplicate primary key for field: %s' % k)
                    primarykey = k
                else:
                    fields.append(k)
        if not primarykey:
            raise Exception('Primary key not found.')
        # 删除类属性
        for k in mappings.keys():
            attrs.pop(k)
        # 保存除主键外的属性名为``（运算出字符串）列表形式
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primarykey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        # 构造默认的 SELECT, INSERT, UPDATE, DELETE语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primarykey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
        tableName, ', '.join(escaped_fields), primarykey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
        tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primarykey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primarykey)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        #返回对象的属性,如果没有对应属性则会调用__getattr__
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                # 把默认属性设置进去
                setattr(self, key, value)
        return value

    # 类方法的第一个参数是cls,而实例方法的第一个参数是self
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                # extend 接收一个iterable参数
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        #调用select函数,返回值是从数据库里查找到的数据结果
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectedField, where=None, args=None):
        ' find number by select and where. '
        # 将列名重命名为 _num_
        sql = ['select %s _num_ from `%s`' % (selectedField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        # 限制结果数量为1
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        # 获取所有value
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)