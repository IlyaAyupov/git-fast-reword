import hashlib
import os
import re
import sys
import zlib
from typing import List, Dict
from queue import Queue


class _LongTag:
    initial_hash: str
    hash_id: str
    parent_hash: str
    initial_parent_hash: str
    text: str
    is_modified: bool = False

    def __init__(self, path, hash_id):
        self.text = zlib.decompress(open(path + hash_id[:2] + '/' + hash_id[2:], "rb").read()).decode('utf-8')
        self.parent_hash = self.text.split('\n')[0].split(' ')[2]
        self.hash_id = hash_id
        self.initial_hash = hash_id
        self.initial_parent_hash = self.parent_hash

    def get_text(self):
        return self.text.replace(self.initial_parent_hash, self.parent_hash)

    def recalc_hash(self):
        self.hash_id = hashlib.sha1(self.get_text().encode('utf-8')).hexdigest()
        return self.hash_id

    def remove_old(self, path):
        os.remove(path + self.initial_hash[:2] + '/' + self.initial_hash[2:])

    def save(self, path: str):
        if not os.path.exists(path + self.hash_id[:2]):
            os.mkdir(path + self.hash_id[:2])
        open(path + self.hash_id[:2] + '/' + self.hash_id[2:], 'wb').write(
            zlib.compress(self.get_text().encode('utf-8')))
        print(self.hash_id)


class _Commit:
    hash_id: str
    old_hash: str
    initial_hash: str
    is_modified: bool = False
    is_modified_on_round: bool = False
    need_modify: bool = False
    tree: str = ""
    author: str = ""
    commiter: str = ""
    comment: str = ""
    parents: list = ""

    def __init__(self, path: str, hash_id: str):
        self.parents = []
        data = zlib.decompress(open(path + hash_id[:2] + '/' + hash_id[2:], "rb").read()).decode(
            'utf-8').strip().split('\n')
        self.tree = data[0]
        comm_start = data.index("")
        self.commiter = data[comm_start - 1]
        self.author = data[comm_start - 2]
        self.comment = ""
        for i in data[comm_start + 1:]:
            self.comment += i + '\n'
        self.comment = self.comment.strip()
        for i in data[1:comm_start - 2]:
            self.parents.append(i.split(' ')[-1])
        self.hash_id = hash_id
        self.initial_hash = hash_id

    def get_string(self) -> str:
        data = self.tree + '\n'
        for parent in self.parents:
            data += "parent " + parent + '\n'
        data += self.author + '\n' + self.commiter + '\n\n' + self.comment + '\n'
        return data

    def change_comment(self, comment: str):
        self.comment = comment
        length = len(self.get_string())
        self.tree = self.tree[:7] + str(length - 11) + self.tree[10:]
        print(self.tree)

    def calc_hash(self) -> str:
        return hashlib.sha1(self.get_string().encode('utf-8')).hexdigest()

    def remove_old(self, path: str):
        os.remove(path + self.initial_hash[:2] + '/' + self.initial_hash[2:])

    def save(self, path: str):
        if not os.path.exists(path + self.hash_id[:2]):
            os.mkdir(path + self.hash_id[:2])
        open(path + self.hash_id[:2] + '/' + self.hash_id[2:], 'wb').write(
            zlib.compress(self.get_string().encode('utf-8')))


def object_type(path: str):
    data = zlib.decompress(open(path, 'rb').read())[:6].decode('utf-8')
    if data == 'commit':  # проверка файла, является ли он коммитом
        return _Commit
    if data[:3] == 'tag':
        return _LongTag
    return None


class Repository:
    path: str = ""
    commits: List[_Commit] = []
    long_tags: List[_LongTag] = []
    graph: List[List[bool]] = []
    changes: Dict[str, str] = {}
    comment_changes: Dict[str, str] = {}
    heads: Dict[str, str] = {}
    head: str = ""
    hash_to_index: Dict[str, int] = {}

    def __init__(self, path: str = "./"):
        self.path = path + '.git/'  # путь к .git
        if not os.path.exists(self.path):
            print(".git not found", file=sys.stderr)
            exit(1)
        self.__load_commits()
        for i in range(len(self.commits)):
            self.hash_to_index.update({self.commits[i].initial_hash:i})

    def __load_commits(self):
        for file in os.listdir(self.path + "/refs/heads"):
            self.heads.update({file: open(self.path + "/refs/heads/" + file).read().strip()})
        head = open(self.path + "HEAD").read().strip()
        if head[:3] == "ref":
            self.head = self.heads[head.split('/')[-1]]
        else:
            self.head = head
        for directory in os.listdir(self.path + "/objects"):
            if len(directory) != 2:
                continue
            for file in os.listdir(self.path + "/objects/" + directory):
                obj_type = object_type(self.path + "/objects/" + directory + '/' + file)
                if obj_type is _Commit:
                    commit = _Commit(self.path + "/objects/", directory + file)
                    self.commits.append(commit)
                if obj_type is _LongTag:
                    tag = _LongTag(self.path + "/objects/", directory + file)
                    self.long_tags.append(tag)

    def get_hash(self, exp: str):
        til_ind=exp.index('~') if ('~' in exp) else -1
        up_ind=exp.index('^') if ('^' in exp) else -1
        if til_ind==-1 and up_ind==-1:
            point=exp
        elif til_ind==-1 or up_ind==-1:
            exp_start=max(til_ind,up_ind)
            point = exp[:exp_start]
            exp = exp[exp_start:]
        else:
            exp_start = min(til_ind, up_ind)
            point = exp[:exp_start]
            exp = exp[exp_start:]
        if point == '@' or point == 'HEAD':
            point = self.head
        elif point in self.heads:
            point = self.heads[point]
        elif not re.match("[a-f0-9]+", point) is None:
            point = self.get_full_hash(point)
        else:
            return -1
        if point==-1:
            return -1
        if til_ind==-1 and up_ind==-1:
            return point

        command_queue = Queue()     #подобие стекового калькулятора для обработки этих странных выражений
        args_queue = Queue()
        args = list(map(lambda x: int(x) if len(x) > 0 else 1, exp.replace('^', '~').split('~')[1:]))
        for i in args:
            args_queue.put(i)
        for i in re.sub('[0-9]', '', exp):
            command_queue.put(i)
        point=self.__get_id_from_hash(point)
        while not command_queue.empty():
            command=command_queue.get()
            arg=args_queue.get()
            if command == '~':
                for i in range(arg):
                    if len(self.commits[point].parents)!=0:
                        point=self.__get_id_from_hash(self.commits[point].parents[0])
                    else:
                        return -1
            elif command == '^':
                if len(self.commits[point].parents)>=arg:
                    point=self.__get_id_from_hash(self.commits[point].parents[arg-1])
                else:
                    return -1
            else:
                return -1
        return self.commits[point].hash_id

    def get_comment(self,hash_id: str):
        return self.commits[self.__get_id_from_hash(hash_id)].comment

    # Составляем ориентированный граф, с направлениями рёбер от потомка к предку
    def __make_graph(self):
        n = len(self.commits)
        buf = []
        for i in range(n):
            buf.append(False)
        for i in range(n):
            self.graph.append(buf.copy())
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if self.commits[j].hash_id in self.commits[i].parents:
                    self.graph[i][j] = True

    #   Ищем узлы графа, которые являются потомками изменяемого коммита
    #   Транспонируем матрицу и получаем ориентированный граф, с направлениями рёбер от предка к потомку
    #   Просто обходим граф от изменяемого коммита. Все посещенные узлы будут изменены

    def __find_change(self, start: int):
        queue = Queue()
        queue.put(start)
        while not queue.empty():
            node = queue.get()
            self.commits[node].need_modify = True
            for i in range(len(self.commits)):
                if self.graph[i][node]:
                    queue.put(i)

    def __make_changes(self, start_hash: str, new_comment: str):
        start = -1
        for i in range(len(self.commits)):
            if self.commits[i].initial_hash == start_hash:
                start = i
        assert start != -1
        self.comment_changes.update({start_hash: new_comment})
        for i in self.commits:
            i.need_modify = False
            i.is_modified_on_round = False
        self.__find_change(start)
        self.commits[start].change_comment(new_comment.strip())
        self.__recalc_hash_recursive(start)
        for i in self.commits:  # раунд закончен, сбрасываем флаги изменений
            i.need_modify = False
            i.is_modified_on_round = False

    def __recalc_hash_recursive(self, start: int):

        for i in range(len(self.commits)):
            if self.graph[start][i] and not self.commits[i].is_modified_on_round and self.commits[i].need_modify:
                return  # проверяем, все ли предки изменены
            if self.graph[start][i] and self.commits[i].is_modified_on_round and (
                    self.commits[i].old_hash in self.commits[start].parents):  # обновляем хеши родителей
                self.commits[start].parents[self.commits[start].parents.index(self.commits[i].old_hash)] = self.commits[
                    i].hash_id

        self.commits[start].is_modified_on_round = True
        self.commits[start].is_modified = True
        self.commits[start].old_hash = self.commits[start].hash_id  # сохраняем старый хеш
        self.commits[start].hash_id = self.commits[start].calc_hash()  # обновляем хеш
        for i in range(len(self.commits)):
            if self.graph[i][start]:
                self.__recalc_hash_recursive(i)  # вызываем функцию для детей

    def __get_id_from_hash(self, id_hash):
        if id_hash in self.hash_to_index:
            return self.hash_to_index[id_hash]
        return -1

    def __update_changes(self):
        for i in self.commits:
            if i.is_modified:
                self.changes.update({i.initial_hash: i.hash_id})

        for i in self.long_tags:
            if i.is_modified:
                self.changes.update({i.initial_hash: i.hash_id})

    def __update_long_tags(self):
        self.__update_changes()
        for i in self.long_tags:
            if i.initial_parent_hash in self.changes:
                i.parent_hash = self.changes[i.initial_parent_hash]
                i.is_modified = True
                i.hash_id = i.recalc_hash()
        self.__update_changes()

    def __update_log(self, path):
        data = open(path).read().split("\n")
        for i in range(len(data)):
            if data[i][41:81] in self.comment_changes:
                buf = data[i].split('\t')
                if buf[1][:6] == 'commit':
                    data[i] = data[i][:len(buf[0]) + buf[1].index(":") + 1] + ": " + self.comment_changes[
                        data[i][41:81]]
            if data[i][:40] in self.changes:
                data[i] = self.changes[data[i][:40]] + data[i][40:]
            if data[i][41:81] in self.changes:
                data[i] = data[i][:41] + self.changes[data[i][41:81]] + data[i][81:]
        file = open(path, 'w')
        for i in data:
            file.write(i + '\n')
        file.close()

    def __update_ref(self, path):
        data = open(path).read().strip()
        if data in self.changes:
            open(path, 'w').write(self.changes[data] + '\n')

    def __write_changes(self):
        self.__update_long_tags()
        for i in self.commits:
            if i.is_modified:
                i.remove_old(self.path + "/objects/")
                i.save(self.path + "/objects/")
        for i in self.long_tags:
            if i.is_modified:
                i.remove_old(self.path + "/objects/")
                i.save(self.path + "/objects/")
        self.__update_log(self.path + "/logs/HEAD")
        for file in os.listdir(self.path + "/logs/refs/heads"):
            self.__update_log(self.path + "/logs/refs/heads/" + file)
        for file in os.listdir(self.path + '/refs/heads'):
            self.__update_ref(self.path + '/refs/heads/' + file)
        for file in os.listdir(self.path + '/refs/tags'):
            self.__update_ref(self.path + '/refs/tags/' + file)
        self.__update_ref(self.path + '/ORIG_HEAD')
        if not re.match("[a-f0-9]", open(self.path + "/HEAD").read().strip()) is None:
            self.__update_ref(self.path + "/HEAD")

    def __remove_empty_dirs(self):
        for directory in os.listdir(self.path + "/objects"):
            if len(directory) != 2:
                continue
            if len(os.listdir(self.path + "/objects/" + directory))==0:
                os.rmdir(self.path + "/objects/"+directory)

    def change_commits(self, hashes: List[str], comments: List[str]):
        self.__make_graph()
        for i in range(len(hashes)):
            self.__make_changes(hashes[i], comments[i])
        self.__write_changes()
        self.__remove_empty_dirs()

    def get_full_hash(self, input_hash):
        for i in self.commits:
            if i.initial_hash[:len(input_hash)] == input_hash:
                return i.initial_hash
        return None
