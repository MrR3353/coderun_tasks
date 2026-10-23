Задачки взяты из https://coderun.yandex.ru/catalog

Запуск теста:
```shell
python3 <номер_задачи>.py < <номер_задачи>.txt
```

Пример (подаем данные на вход и проверяем вывод):
```shell
python3 3.py < 3_in.txt | diff - 3_out.txt && echo "MATCH"
```