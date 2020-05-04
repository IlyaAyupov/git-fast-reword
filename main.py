import argparse
import random
import string
from Repository import *


def random_str(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def from_file(repo: Repository, file: str):
    try:
        data = open(file).read().strip().split('\n')
    except IOError:
        print(f"file {file} not found", file=sys.stderr)
        exit(1)
    hashes: List[str] = []
    comments: List[str] = []
    for i, j in zip(data, range(len(data))):
        if ' ' in i:
            index = i.index(' ')
            hash_id = repo.get_hash(i[:index])
            if hash_id == -1:
                print(f"Commit on line {j + 1} not found", file=sys.stderr)
                exit(1)
            hashes.append(hash_id)
            comments.append(i[index + 1:])
        else:
            print(f"Delimiter on line {j + 1} not found", file=sys.stderr)
            exit(1)
    repo.change_commits(hashes, comments)


def from_list(repo: Repository, commits: List[str]):
    tmp = f"tmp-{random_str(40)}"                   #запишем строки во временный файл
    file = open(tmp, 'w')
    for i in commits:
        hash_id = repo.get_hash(i)
        if hash_id == -1:
            print(f"Commit \"{i}\" not found", file=sys.stderr)
            exit(1)
        file.write(f"{hash_id[:7]} {repo.get_comment(hash_id)}\n")
    file.close()
    os.system(f"$EDITOR {tmp}")                     #вызовем редактор по умолчанию
    from_file(repo, tmp)                            #вызываем изменения из файла
    os.remove(tmp)                                  #удаляем файл

#тут всё просто
def from_cli(repo: Repository, hash_str: str, comment: str):
    hash_id = repo.get_hash(hash_str)
    if hash_id == -1:
        print(f"Commit not found", file=sys.stderr)
        exit(1)
    repo.change_commits([hash_id], [comment])


# икона от репозиториев с SHA-256 вместо SHA-1
# .______________________________________________.
# | [~~-__]        _______         [~~-__]       |
# | . . .-,    _-~~       ~~-_     .-,    ,      |
# | |Y| |-' _-~    _______    ~-_  +-+ \ /       |
# | ` ' '  /    _zZ=zzzzz=Zz_    \ `-'  6        |
# |       /    // /~    *~\ \\    \              |
# |      f    ff f _-zzz--_] ??    ?     -- --   |
# |      |    || L/ -=6,)_--L|j    |     IC XC   |
# |      |    ||/f     //`9=-7    _L-----__      |
# |      t    |( |    </   //  _-~ _____/o 7-_   |
# |       \   | )t   --_ ,'/  /w~-<_____ ~Y   \  |
# |        \  |( |\_   _/ f  f~-_f_   __\  ?   ? |
# |         ~-j \|  ~~~\ /|  |   `6) 6=-'? |   | |
# |       __-~   \______Y |_-|   f<      t |   | |
# |    _zZ   *    \    /  /  t   t =    / \j~-_j |
# |  ,'   ~-_     _\__/__/_   \   >-r--~  J-_N/  |
# | /f       T\  ( )_______)   ~-<  L   ,' \-~   |
# |f |       | \  \Cyg npa\___---~~7 ~~~ ___T\   |
# f| |       | |T\ \BegeHz \      /     /   ) \  |
# || |       | || ~\\cygumc--_   f     /   /|  \ |
# || |_______| ||   ~\mu^oE__ \_r^--__<~- / j   ?|
# || /       \ j|     \u wegp\__|    | \ / /    ||
# |f/~~~~~~~-zZ_L_.   _\_______\`_     _/ /|    ||
# |Y  ,     ff    |~~T--_/~       ~---~  / j    ||
# ||f t     jj    |  |(  \   ~-r______--~ /     t|
# |t|  \___//_____|~~~7\  \   f ff    _--~       ?
# | Y    ,'/    _<   /  \\\\  | jj   / ~-_       |
# | |   / f c-~~  ~-<____UUU--~~~_--~     \      |
# |_|__f__|__````-----'_________/__________?_____|
arguments = sys.argv[1:]
parser = argparse.ArgumentParser(description='Fast reword for git')
hash_id = None
comment = ""
parser.add_argument('-f', action="store", dest="file_path", help="path to file with list of changes")
parser.add_argument('-c', action="store", dest="directory", default="./", type=str,help="path to repo directory")
parser.add_argument('-l',dest="commit_list", nargs='*', help="commits list to reword")
if len(arguments) > 1:
    if arguments[0][0] != '-' and arguments[1][0] != '-':
        hash_id=arguments[0]
        comment=arguments[1]
        if len(arguments) > 2:
            arguments = arguments[2:]
        else:
            arguments = []

args = parser.parse_args(arguments)
repo=Repository(args.directory+'/'*(args.directory[-1]!='/'))
if not hash_id is None:
    from_cli(repo,hash_id,comment)
    exit(0)
if not args.file_path is None:
    from_file(repo,args.file_path)
    exit(0)
if len(args.commit_list)>0:
    from_list(repo,args.commit_list)
    exit(0)
print("Not enough arguments",file=sys.stderr)
exit(1)