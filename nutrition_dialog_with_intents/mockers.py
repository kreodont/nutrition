def mock_incoming_event(
        *,
        phrase: str,
        has_screen: bool = True,
        is_new_session: bool = False,
) -> dict:
    if has_screen:
        interfaces = {"screen": {}}
    else:
        interfaces = {}

    if is_new_session:
        message_id = 0
    else:
        message_id = 3
    return {
        "meta": {
            "client_id": "ru.yandex.searchplugin/7.16 (none none; android "
                         "4.4.2)",
            "interfaces": interfaces,
            "locale": "ru-RU",
            "timezone": "UTC"
        },
        "request": {
            "command": phrase,
            "nlu": {
                "entities": [],
                "tokens": phrase.lower().split()
            },
            "original_utterance": phrase,
            "type": "SimpleUtterance"
        },
        "session": {
            "message_id": message_id,
            "new": is_new_session,
            "session_id": "2600748f-a3029350-a94653be-1508e64a",
            "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
            "user_id": "E401738E621D9AAC04AB162E44F39B3"
                       "ABDA23A5CB2FF19E394C1915ED45CF467"
        },
        "version": "1.0"
    }
