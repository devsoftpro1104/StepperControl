# controller_app

Хост-приложение управления контроллером шагового двигателя.

## Запуск
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m controller_app
```

## Тесты
```
pytest
```

## Сборка ресурсов Qt
```
pyrcc6 resources/resources.qrc -o src/controller_app/resources_rc.py
```