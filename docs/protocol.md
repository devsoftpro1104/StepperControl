# Протокол обмена

Бинарный TLV-протокол поверх UART/USB-CDC/TCP.
Первоисточник: [shared/protocol/protocol.yaml](../shared/protocol/protocol.yaml).
Заголовки/коды/CRC генерируются скриптами `generate_c.py` и `generate_py.py`.

См. также:
- [adr/0003-protocol-binary-tlv.md](adr/0003-protocol-binary-tlv.md) — почему бинарный.
- [cli.md](cli.md) — параллельный текстовый shell-канал на том же UART (для
  отладки в терминале и упрощённой интеграции GUI). Бинарный и текстовый
  протоколы независимы; парсер хоста выбирает один из них на сессию.

## Кадр
| Поле     | Размер | Описание                    |
|----------|--------|-----------------------------|
| SOF      | 1      | 0xA5                        |
| Len      | 2      | длина payload (LE)          |
| Cmd/Resp | 1      | код команды/ответа          |
| Seq      | 1      | номер запроса 0..255        |
| Payload  | N      | TLV-поля                    |
| CRC16    | 2      | CCITT-FALSE по Cmd..Payload |