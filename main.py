import random
import asyncio
from telebot.async_telebot import AsyncTeleBot
import sqlite3
from funcs import shuffled, db_request_fetchone, db_request_fetchall

conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
  user_id INT,
  words TEXT,
  testing INT DEFAULT 0, 
  answer TEXT,
  errors DEFAULT 0,
  count_of_words INT DEFAULT 0,
  first_and_correct INT DEFAULT 0,
  incorrect_words_list TEXT DEFAULT '',
  percent_of_first_and_correct REAL DEFAULT 0
);''')
cursor.close()
conn.commit()
conn.close()


with open("token.txt", "r", encoding="utf-8") as f:
    token = f.readline()
bot = AsyncTeleBot(token)


@bot.message_handler(commands=['start'])
async def start_training(message):
    with open('words.txt', "r", encoding="utf-8") as f:
        if len(db_request_fetchall("database.db", "SELECT user_id FROM users WHERE user_id = ?", (message.chat.id,))) == 0:
            #добавление айди пользователя, список его слов и правильный ответ на данный момент
            db_request_fetchall("database.db",
                                "INSERT INTO users (user_id, words, testing) VALUES (?, ?, ?)",
                                (message.chat.id, str(shuffled(f.read().rstrip().split()))[2:-2], 1))
            db_request_fetchone("database.db",
                                "UPDATE users SET answer = ? WHERE user_id = ?",
                                (str(db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")[0]), message.chat.id))
    #приветственное сообщение
    await bot.send_message(message.chat.id,
                           "Привет, давай начнем тренировку по расстановке ударений в Русском языке!\n"
                           "~~~~~~~~~~\n"
                           "Твоя задача - отправлять мне слово с поставленным ударением.\n"
                           "~~~~~~~~~~\n"
                           "Вот пример использования:\n\n"
                           "Я: лекторов\n"
                           "Ты: лЕкторов\n"
                           "~~~~~~~~~~\n"
                           'Чтобы остановить тренировку, напиши "Стоп".'
                           )
    #отправка пользователю слова-вопроса
    await bot.send_message(message.chat.id, db_request_fetchone("database.db",
                                                                "SELECT answer FROM users WHERE user_id = ?",
                                                                (message.chat.id,))[0].lower())
    #установка параметра testing на 1 для того, чтобы хранить состояние пользователя(тренируется сейчас или нет)
    if db_request_fetchone("database.db","SELECT testing FROM users WHERE user_id = ?",(message.chat.id,))[0] == 0:
        db_request_fetchone("database.db", "UPDATE users SET testing = ? WHERE user_id = ?", (1, message.chat.id))


@bot.message_handler()
async def get_message(message):
    a = "', '"
    b = ', '

    #проверка состояния тренировки пользователя (тренируется сейчас или нет)
    if len(db_request_fetchall("database.db", "SELECT testing FROM users WHERE user_id = ?", (message.chat.id, ))) == 0:
        await bot.send_message(message.chat.id, 'Для начала тренировки введите /start')
        return

    #если пользователь хочет завершить тренировку (написал "стоп")
    if message.text.upper() == 'СТОП':

        #пробуем расчитать процент количества правильных ответов с первой попытки (количество ответов с 1 попытки/количество слов)
        try:
            db_request_fetchone("database.db", "SELECT first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))
            db_request_fetchone("database.db", "SELECT count_of_words FROM users WHERE user_id = ?", (message.chat.id,))
            db_request_fetchone("database.db",
                                "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?",
                                (int(db_request_fetchone("database.db", "SELECT first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))[0] / db_request_fetchone("database.db", "SELECT count_of_words FROM users WHERE user_id = ?", (message.chat.id,))[0] * 100), message.chat.id))

        #если количество слов = 0 (тогда и процентаж правильных ответов с 1 попытки = 0)
        except ZeroDivisionError:
            db_request_fetchone("database.db", "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?", ("0", message.chat.id))

        #если список слов, который пользователь ввел неправильно = 0, то мы должны вывести "таких слов в не встретилось"
        if len(db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")) < 2:
            db_request_fetchone("database.db", "UPDATE users SET incorrect_words_list = ? WHERE user_id = ?", ("таких не встретилось", message.chat.id))

        #вывод результатов тренировки
        await bot.send_message(message.chat.id,
                               'Тренировка завершена!\n'
                               '~~~~~~~~~~\n'
                               'Ваши результаты:\n'
                               f'Всего уникальных слов: {db_request_fetchone("database.db", "SELECT count_of_words FROM users WHERE user_id = ?", (message.chat.id,))[0]}\n'
                               f'Всего ошибок: {db_request_fetchone("database.db", "SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))[0]}\n'
                               f'Правильных ответов с 1 попытки: {db_request_fetchone("database.db", "SELECT first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))[0]} ({db_request_fetchone("database.db", "SELECT percent_of_first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))[0]}%)\n'
                               f'Слова, с которыми возникли трудности: {b.join(db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split(a))}\n'
                               '~~~~~~~~~~\n'
                               'Для нового сеанса введите /start'
                               )

        #удаление пользователя из бд
        db_request_fetchone("database.db", "DELETE FROM users WHERE user_id = ?", (message.chat.id,))
        return

    #если пользователь ввел текст
    if message.content_type == 'text':

        #если слова в списке для слов еще есть
        if db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '"):

            #если слова нету в списке для неправильно написанных слов, то добавляем +1 к счетчику уникальных слов
            if db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0] not in db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '"):
                db_request_fetchone("database.db", "UPDATE users SET count_of_words = count_of_words + 1 WHERE user_id = ?", (message.chat.id,))

            #проверяем, правильный ли ответ
            if (message.text[1:] == db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0][1:] and
                    message.text[0].lower() == db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0][0].lower()):

                #удаляем слово из списка слов
                db_request_fetchone("database.db", "UPDATE users SET words = ? WHERE user_id = ?", (str(db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")[1:])[2:-2], message.chat.id))

                #выводим сообщение о верном ответе
                await bot.send_message(message.chat.id, "Верно!")

                #если слова нету в списке для неправильно написанных слов, то добавляем +1 к счетчику правильных ответов с 1 попытки
                if db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0] not in db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '"):
                    db_request_fetchone("database.db", "UPDATE users SET first_and_correct = first_and_correct + 1 WHERE user_id = ?", (message.chat.id,))

                #если в списке для слов еще есть слова, то подготавливаем ответ для следующего задания
                if db_request_fetchone("database.db","SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")[0] != '':
                    db_request_fetchone("database.db", "UPDATE users SET answer = ? WHERE user_id = ?", (db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")[0], message.chat.id))

                    #отправляем следующее задание
                    await bot.send_message(message.chat.id, db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id, ))[0].lower())

                #если слова в списке для слов закончились
                else:
                    # пробуем расчитать процент количества правильных ответов с первой попытки (количество ответов с 1 попытки/количество слов)
                    try:
                        db_request_fetchone("database.db", "SELECT first_and_correct FROM users WHERE user_id = ?",
                                            (message.chat.id,))
                        db_request_fetchone("database.db", "SELECT count_of_words FROM users WHERE user_id = ?",
                                            (message.chat.id,))
                        db_request_fetchone("database.db",
                                            "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?",
                                            (int(db_request_fetchone("database.db",
                                                                     "SELECT first_and_correct FROM users WHERE user_id = ?",
                                                                     (message.chat.id,))[0] /
                                                 db_request_fetchone("database.db",
                                                                     "SELECT count_of_words FROM users WHERE user_id = ?",
                                                                     (message.chat.id,))[0] * 100), message.chat.id))

                    # если количество слов = 0 (тогда и процентаж правильных ответов с 1 попытки = 0)
                    except ZeroDivisionError:
                        db_request_fetchone("database.db",
                                            "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?",
                                            ("0", message.chat.id))

                    # если список слов, который пользователь ввел неправильно = 0, то мы должны вывести "таких слов в не встретилось"
                    if len(db_request_fetchone("database.db",
                                               "SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                               (message.chat.id,))[0].split("', '")) < 2:
                        db_request_fetchone("database.db",
                                            "UPDATE users SET incorrect_words_list = ? WHERE user_id = ?",
                                            ("таких не встретилось", message.chat.id))

                    # вывод результатов тренировки
                    await bot.send_message(message.chat.id,
                                           'Тренировка завершена!\n'
                                           '~~~~~~~~~~\n'
                                           'Ваши результаты:\n'
                                           f'Всего уникальных слов: {db_request_fetchone("database.db", "SELECT count_of_words FROM users WHERE user_id = ?", (message.chat.id,))[0]}\n'
                                           f'Всего ошибок: {db_request_fetchone("database.db", "SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))[0]}\n'
                                           f'Правильных ответов с 1 попытки: {db_request_fetchone("database.db", "SELECT first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))[0]} ({db_request_fetchone("database.db", "SELECT percent_of_first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))[0]}%)\n'
                                           f'Слова, с которыми возникли трудности: {b.join(db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split(a))}\n'
                                           '~~~~~~~~~~\n'
                                           'Для нового сеанса введите /start'
                                           )

                    # удаление пользователя из бд
                    db_request_fetchone("database.db", "DELETE FROM users WHERE user_id = ?", (message.chat.id,))
                    return
            else:
                #сообщаем о том, что слово неверное
                await bot.send_message(message.chat.id, f'Неверно, слово {db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0].split(a)[0]} попадется вам еще раз!')

                #добавляем слово в список для неверных слов
                if db_request_fetchone("database.db","SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0] not in db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '"):
                    db_request_fetchone("database.db", "UPDATE users SET incorrect_words_list = ? WHERE user_id = ?", (str(db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0])+ "', '" + str(db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?",(message.chat.id,))[0]), message.chat.id))

                #увеличиваем счетчик ошибок на +1
                db_request_fetchone("database.db", "UPDATE users SET errors = errors + 1 WHERE user_id = ?", (message.chat.id,))

                #перемешиваем список для слов
                db_request_fetchone("database.db", "UPDATE users SET words = ? WHERE user_id = ?", (str(shuffled(db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")))[2:-2], message.chat.id))

                #устанавливаем новый правильный ответ для следующего задания
                db_request_fetchone("database.db", "UPDATE users SET answer = ? WHERE user_id = ?", (db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split("', '")[0], message.chat.id))

                #отсылаем новое задание
                await bot.send_message(message.chat.id, db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0].lower())
                return

    #если пользователь отправил не текст (засчитываем за неправильный ответ)
    else:
        # сообщаем о том, что слово неверное
        await bot.send_message(message.chat.id,
                               f'Неверно, слово {db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[0].split(a)[0]} попадется вам еще раз!')

        # добавляем слово в список для неверных слов
        if db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[
            0] not in db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                          (message.chat.id,))[0].split("', '"):
            db_request_fetchone("database.db", "UPDATE users SET incorrect_words_list = ? WHERE user_id = ?", (str(
                db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))[
                    0]) + "', '" + str(
                db_request_fetchone("database.db", "SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                    (message.chat.id,))[0]), message.chat.id))

        # увеличиваем счетчик ошибок на +1
        db_request_fetchone("database.db", "UPDATE users SET errors = errors + 1 WHERE user_id = ?", (message.ch.id,))

        # перемешиваем список для слов
        db_request_fetchone("database.db", "UPDATE users SET words = ? WHERE user_id = ?", (str(shuffled(
            db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[
                0].split("', '")))[2:-2], message.chat.id))

        # устанавливаем новый правильный ответ для следующего задания
        db_request_fetchone("database.db", "UPDATE users SET answer = ? WHERE user_id = ?", (
        db_request_fetchone("database.db", "SELECT words FROM users WHERE user_id = ?", (message.chat.id,))[0].split(
            "', '")[0], message.chat.id))

        # отсылаем новое задание
        await bot.send_message(message.chat.id,
                               db_request_fetchone("database.db", "SELECT answer FROM users WHERE user_id = ?",
                                                   (message.chat.id,))[0].lower())
        return

#запускаем бота
async def main():
    await bot.infinity_polling(timeout=1000)
try:
    if __name__ == "__main__":
        asyncio.run(main())
except TimeoutError as e:
    print(e)
    if __name__ == "__main__":
        asyncio.run(main())