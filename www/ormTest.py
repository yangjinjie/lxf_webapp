import logging; logging.basicConfig(level=logging.INFO)
from models import User
import asyncio
import orm

loop = asyncio.get_event_loop()

# 插入
# async def insert():
#     await orm.create_pool(loop,user='root', password='111111', db='awesome')
#
#     u = User(name='Test3', email='test3@example.com', passwd='123890', image='ab32out:blank')
#
#     await u.save()
#
#     r = await User.findAll()
#     print(r)

#删除
# async def remove():
#     await orm.create_pool(loop, user='root', password='password', db='awesome')
#     r = await User.find('001492757565916ec72f6eeb731405ab07ee37911a3ae79000')
#     await r.remove()
#     print('remove',r)
#     await orm.destory_pool()

#更新
# async def update():
#     await orm.create_pool(loop, user='root', password='password', db='awesome')
#     r = await User.find('00149276202953187d8d3176f894f1fa82d9caa7d36775a000')
#     r.passwd = '765'
#     await r.update()
#     print('update',r)
#     await orm.destory_pool()


async def find():
    await orm.create_pool(loop, user='root', password='111111', db='awesome')
    all = await User.findAll()
    print(all)
    pk = await User.find('0015010327585118294b70b9dc248fb8bf6ccb6d6e071ce000')
    print(pk)
    num = await User.findNumber('email')
    print(num)
    await orm.destory_pool()

# loop.run_until_complete(insert())
loop.run_until_complete(find())
loop.close()


