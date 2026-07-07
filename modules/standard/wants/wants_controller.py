from core.command_param_types import Any, Int, Const, Options, Item, Character
from core.decorators import instance, command
from core.chat_blob import ChatBlob
import time


@instance()
class WantsController:
    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.alts_service = registry.get_instance("alts_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS wants ("
                     "id INT PRIMARY KEY AUTO_INCREMENT, "
                     "char_id INT NOT NULL, "
                     "want TEXT NOT NULL,"
                     "created_at INT NOT NULL)")

    @command(command="wants", params=[], access_level="all",
             description="Show your wants")
    def wants_list_cmd(self, request):
        # Show wants for the current character only
        data = self.db.query("SELECT w.*, p.name AS char_name FROM wants w LEFT JOIN player p ON w.char_id = p.char_id WHERE w.char_id = ? ORDER BY w.created_at DESC", [request.sender.char_id])
        cnt = len(data)
        blob = ""
        for row in data:
            blob += "%s %s\n\n" % (row.want, self.text.make_tellcmd("Remove", "wants remove %d" % row.id))

        return ChatBlob("Wants for %s (%d)" % (request.sender.name, cnt), blob)

    @command(command="wants", params=[Const("alts")], access_level="all",
             description="Show wants for all your alts")
    def wants_alts_cmd(self, request, _):
        # Show wants for all alts (previous behavior of bare 'wants')
        alts = self.alts_service.get_alts(request.sender.char_id)

        cnt = 0
        blob = ""
        main_name = alts[0].name
        for alt in alts:
            data = self.db.query("SELECT w.*, p.name AS char_name FROM wants w LEFT JOIN player p ON w.char_id = p.char_id WHERE w.char_id = ? ORDER BY w.created_at DESC", [alt.char_id])
            alt_cnt = len(data)
            cnt += alt_cnt

            if alt_cnt:
                for row in data:
                    blob += "<highlight>%s</highlight> (%s) %s %s\n\n" % ((row.char_name or alt.char_id), main_name, row.want, self.text.make_tellcmd("Remove", "wants remove %d" % row.id))

        return ChatBlob("Wants for %s (%d)" % (main_name, cnt), blob)

    @command(command="wants", params=[Const("add"), Any("item")], access_level="all",
             description="Add a want")
    def wants_add_cmd(self, request, _, want):
        self.db.exec("INSERT INTO wants (char_id, want, created_at) VALUES (?, ?, ?)", [request.sender.char_id, want, int(time.time())])

        return "Want added successfully."

    @command(command="wants", params=[Character("character"), Any("item")], access_level="all",
             description="Add a want for one of your alts")
    def wants_add_for_char_cmd(self, request, character, want):
        if not character.char_id:
            return "Could not find character <highlight>%s</highlight>." % character.name

        # only allow adding wants for characters in your alt group
        if self.alts_service.get_main(request.sender.char_id).char_id != self.alts_service.get_main(character.char_id).char_id:
            return "You may only add wants for your own alts."

        self.db.exec("INSERT INTO wants (char_id, want, created_at) VALUES (?, ?, ?)", [character.char_id, want, int(time.time())])

        return "Want added successfully for <highlight>%s</highlight>." % character.name

    @command(command="wants", params=[Options(["rem", "remove"]), Int("want_id")], access_level="all",
             description="Remove a want")
    def wants_remove_cmd(self, request, _, want_id):
        want = self.db.query_single("SELECT n.*, p.name FROM wants n LEFT JOIN player p ON n.char_id = p.char_id WHERE n.id = ?", [want_id])

        if not want:
            return "Could not find want with ID <highlight>%d</highlight>." % want_id

        if self.alts_service.get_main(request.sender.char_id).char_id != self.alts_service.get_main(want.char_id).char_id:
            return "You must be a confirmed alt of <highlight>%s</highlight> to remove this want." % want.name

        self.db.exec("DELETE FROM wants WHERE id = ?", [want_id])

        return "Want with ID <highlight>%d</highlight> deleted successfully." % want_id

    @command(command="wants", params=[Const("search"), Item("item")], access_level="all",
             description="Search wants by itemref")
    def wants_search_itemref_cmd(self, request, _, item):
        return self.search_wants(item.name)

    @command(command="wants", params=[Const("search"), Any("name")], access_level="all",
             description="Search wants by name")
    def wants_search_name_cmd(self, request, _, wants_search):
        return self.search_wants(wants_search)

    def search_wants(self, wants_search):
        wants = self.db.query(
            "SELECT w.*, p.name AS char_name FROM wants w LEFT JOIN player p ON w.char_id = p.char_id WHERE w.want LIKE ? ORDER BY w.char_id",
            ["%" + wants_search + "%"])

        # group by main
        groups = {}
        for want in wants:
            alts = self.alts_service.get_alts(want.char_id)
            main_name = alts[0].name
            groups.setdefault(main_name, []).append(want)

        blob = ""
        for main_name, wants_list in groups.items():
            blob += "<header2>%s</header2>\n" % main_name
            for w in wants_list:
                blob += "<highlight>%s</highlight> %s\n\n" % (w.char_name or w.char_id, w.want)

        return ChatBlob("Search Results (%d)" % len(wants), blob)

    @command(command="wants", params=[Const("all")], access_level="all",
             description="Shows all wants")
    def wants_all_cmd(self, request, _):
        sql = ("SELECT w.*, p.name FROM wants w "
               "LEFT JOIN alts a ON w.char_id = a.char_id "
               "LEFT JOIN alts a2 ON (a2.group_id = a.group_id AND a2.status = 2) "
               "LEFT JOIN player p ON p.char_id = COALESCE(a2.char_id, w.char_id) "
               "ORDER BY p.name ASC")

        data = self.db.query(sql)

        blob = ""
        current_main_name = ""
        for want in data:
            if want.name != current_main_name:
                blob += "\n<header2>%s</header2>\n" % want.name
                current_main_name = want.name

            blob += want.want + "\n"

        return ChatBlob("Wants List (%d)" % len(data), blob)
