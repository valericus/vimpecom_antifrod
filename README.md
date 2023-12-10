[AGI](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/Dialplan_Applications/AGI/) скрипт для
антифрод платформы Билайн.
Делает запрос в соответсвующее API для регистрации исходящего звонка в антифрод системе и для проверки входящего.
В случае неуспешной проверки прерывает звонок. Так же делает запись в VERBOSE лог на каждое действие.

**Скрипт находится на стадии активной разработки, используйте на свой страх и риск.**

## Регистрация звонка

```
same => n,AGI(/opt/vimpelcom_antofrod/antifrod.py register -H your-prod-env-hsot.vimpelcom.ru)
```

## Проверка звонка

```
same => n,AGI(/opt/vimpelcom_antofrod/antifrod.py check -H your-prod-env-hsot.vimpelcom.ru)
```
