import datetime
import hashlib
start_time = datetime.datetime.strptime(
        '2019-03-20 09:51:00',
        '%Y-%m-%d %H:%M:%S',
)
target_time = datetime.datetime.now()
# target_time = datetime.datetime.strptime(
#         '2019-03-21 08:40:00',
#         '%Y-%m-%d %H:%M:%S',
# )
start_x = 19
start_y = 4
while start_time < target_time:
    start_y += 1
    if start_y > 27:
        start_x += 1
        start_y = 3
    if start_x > 32:
        start_x = 3
    start_time += datetime.timedelta(minutes=5)
print(f'{start_x}:{start_y}')


s = '52b29d5e-526c41b3-a0949c99-3778069e'
print(int(hashlib.sha1(s.encode()).hexdigest(), 16) % (10 ** 3))