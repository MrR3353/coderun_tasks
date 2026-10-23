Задачки взяты из https://coderun.yandex.ru/catalog

## Структура

Каждая задача `N` лежит в своей папке:
```
tasks/N/solution.py
tasks/N/tests/1_in.txt
tasks/N/tests/1_out.txt
tasks/N/tests/2_in.txt
tasks/N/tests/2_out.txt
...
```

## Тесты

Прогнать тест вручную: (подаем данные на вход и проверяем вывод):
```shell
python3 tasks/3/solution.py < tasks/3/tests/1_in.txt | diff - tasks/3/tests/1_out.txt && echo "MATCH"
```

Прогнать все тесты всех задач:
```shell
python3 run_tests.py
```

Прогнать все тесты конкретной задачи (можно перечислить несколько):
```shell
python3 run_tests.py 3
python3 run_tests.py 1 3
```

Раннер можно использовать и из кода:
```python
from run_tests import run_task_tests, run_all

run_task_tests(3)  # все тесты задачи 3
run_all()           # все тесты всех задач
```

Скрипт завершается с кодом `0`, если все тесты прошли, и `1` — если хотя бы один упал.
