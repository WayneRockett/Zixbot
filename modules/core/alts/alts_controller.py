from core.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Character, Multiple, NamedParameters
from core.decorators import instance, command
from core.standard_message import StandardMessage


@instance()
class AltsController:
    SORT_OPTIONS = ["level", "name", "profession"]

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.alts_service: AltsService = registry.get_instance("alts_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    @command(command="alts", params=[NamedParameters(["sort_by"])], access_level="all",
             description="Show your alts",
             extended_description="Sort_by param can be one of: " + ", ".join(SORT_OPTIONS))
    def alts_list_cmd(self, request, named_params):
        if named_params.sort_by:
            if named_params.sort_by not in self.SORT_OPTIONS:
                return "sort_by parameter must be one of: " + ", ".join(self.SORT_OPTIONS)
        else:
            named_params.sort_by = "level"

        alts = self.alts_service.get_alts(request.sender.char_id, named_params.sort_by)
        blob = self.format_alt_list(alts, named_params.sort_by, "alts")

        return ChatBlob(f"Alts of {alts[0].name} ({len(alts)})", blob)

    def get_alt_status(self, status):
        if status == AltsService.MAIN:
            return " - [main]"
        else:
            return ""

    @command(command="alts", params=[Const("setmain")], access_level="all",
             description="Set a new main",
             extended_description="You must run this from the character you want to be your new main")
    def alts_setmain_cmd(self, request, _):
        msg, result = self.alts_service.set_as_main(request.sender.char_id)

        if result:
            return f"Character <highlight>{request.sender.name}</highlight> has been set as your main."
        elif msg == "not_an_alt" or msg == "already_main":
            return f"Error! Character <highlight>{request.sender.name}</highlight> is already set as your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Const("add"), Multiple(Character("character"))], access_level="all",
             description="Add one or more alts")
    def alts_add_cmd(self, request, _, alt_chars):
        responses = []
        for alt_char in alt_chars:
            if not alt_char.char_id:
                responses.append(StandardMessage.char_not_found(alt_char.name))
            elif alt_char.char_id == request.sender.char_id:
                responses.append("Error! You cannot register yourself as an alt.")
            else:
                msg, result = self.alts_service.add_alt(request.sender.char_id, alt_char.char_id)
                if result:
                    self.bot.send_private_message(alt_char.char_id,
                                                  f"Character <highlight>{request.sender.name}</highlight> has added you as an alt.",
                                                  conn=request.conn)
                    responses.append(f"Character <highlight>{alt_char.name}</highlight> has been added as your alt.")
                elif msg == "another_main":
                    responses.append(f"Error! Character <highlight>{alt_char.name}</highlight> already has alts.")
                else:
                    raise Exception("Unknown msg: " + msg)

        return "\n".join(responses)

    @command(command="alts", params=[Options(["rem", "remove"]), Character("character")], access_level="all",
             description="Remove an alt")
    def alts_remove_cmd(self, request, _, alt_char):
        if not alt_char.char_id:
            return StandardMessage.char_not_found(alt_char.name)

        msg, result = self.alts_service.remove_alt(request.sender.char_id, alt_char.char_id)
        if result:
            return f"Character <highlight>{alt_char.name}</highlight> has been removed as your alt."
        elif msg == "not_alt":
            return f"Error! Character <highlight>{alt_char.name}</highlight> is not your alt."
        elif msg == "remove_main":
            return "Error! You cannot remove your main."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="alts", params=[Character("character"), NamedParameters(["sort_by"])], access_level="member",
             description="Show alts of another character", sub_command="show",
             extended_description="Sort_by param can be one of: " + ", ".join(SORT_OPTIONS))
    def alts_list_other_cmd(self, request, char, named_params):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if named_params.sort_by:
            if named_params.sort_by not in self.SORT_OPTIONS:
                return "Sort_by parameter must be one of: " + ", ".join(self.SORT_OPTIONS)
        else:
            named_params.sort_by = "level"

        alts = self.alts_service.get_alts(char.char_id, named_params.sort_by)
        blob = self.format_alt_list(alts, named_params.sort_by, f"alts {char.name}")

        return ChatBlob(f"Alts of {alts[0].name} ({len(alts)})", blob)

    @command(command="altadmin", params=[Const("add"), Character("main"), Character("alt")],
             access_level="moderator",
             description="Add alts to main")
    def altadmin_add_cmd(self, request, _, main, alt):
        if not main.char_id:
            return StandardMessage.char_not_found(main.name)
        if not alt.char_id:
            return StandardMessage.char_not_found(alt.name)

        elif main.char_id == alt.char_id:
            return "Error! Alt and main are identical."

        msg, result = self.alts_service.add_alt(main.char_id, alt.char_id)
        if result:
            return f"Character <highlight>{alt.name}</highlight> was added as an alt of <highlight>{main.name}</highlight> successfully."
        elif msg == "another_main":
            return f"Error! Character <highlight>{alt.name}</highlight> already has alts."
        else:
            raise Exception("Unknown msg: " + msg)

    @command(command="altadmin", params=[Options(["rem", "remove"]), Character("main"), Character("alt")],
             access_level="moderator",
             description="Remove alts from main")
    def altadmin_remove_cmd(self, request, _, main, alt):
        if not main.char_id:
            return StandardMessage.char_not_found(main.name)
        if not alt.char_id:
            return StandardMessage.char_not_found(alt.name)

        msg, result = self.alts_service.remove_alt(main.char_id, alt.char_id)

        if result:
            return f"Character <highlight>{alt.name}</highlight> was added as an alt of <highlight>{main.name}</highlight> successfully."
        elif msg == "not_alt":
            return f"Error! Character <highlight>{alt.name}</highlight> is not an alt of <highlight>{main.name}</highlight>."
        elif msg == "remove_main":
            return "Error! Main characters may not be removed from their alt list."
        else:
            raise Exception("Unknown msg: " + msg)

    def get_title_level(self, level):
        if level < 15:
            return 1
        elif level < 50:
            return 2
        elif level < 100:
            return 3
        elif level < 150:
            return 4
        elif level < 190:
            return 5
        elif level < 205:
            return 6
        else:
            return 7

    def get_colored_faction(self, faction):
        if faction == "Omni":
            return "<blue>Omni</blue>"
        elif faction == "Neutral":
            return "<white>Neutral</white>"
        elif faction == "Clan":
            return "<orange>Clan</orange>"
        return faction

    def format_alt_entry(self, alt):
        faction = self.get_colored_faction(alt.faction)
        line = "<highlight>%s</highlight> (%d / <green>%d</green>) %s %s" % (
            alt.name, alt.level, alt.ai_level, faction, alt.profession)
        if self.buddy_service.is_online(alt.char_id):
            line += " [<green>Online</green>]"
        return line

    def format_alt_list(self, alts, sort_by, sort_cmd_prefix):
        sort_links = []
        for option in self.SORT_OPTIONS:
            if option == sort_by:
                sort_links.append(f"<highlight>{option.capitalize()}</highlight>")
            else:
                sort_links.append(self.text.make_tellcmd(option.capitalize(), f"{sort_cmd_prefix} --sort_by={option}"))
        blob = "Sort by: " + " | ".join(sort_links) + "\n\n"

        if sort_by == "level":
            alts_by_tl = {}
            for alt in alts:
                tl = self.get_title_level(alt.level)
                alts_by_tl.setdefault(tl, []).append(alt)

            for tl_alts in alts_by_tl.values():
                tl_alts.sort(key=lambda a: (-a.level, -a.ai_level, a.name.lower()))

            for tl in range(7, 0, -1):
                blob += f"<yellow>TITLE LEVEL {tl}</yellow>\n"
                for alt in alts_by_tl.get(tl, []):
                    blob += self.format_alt_entry(alt) + "\n"
                blob += "\n"
        else:
            prev_profession = None
            for alt in alts:
                if sort_by == "profession" and prev_profession is not None and alt.profession != prev_profession:
                    blob += "\n"
                prev_profession = alt.profession

                blob += self.format_alt_entry(alt) + "\n"
        return blob
