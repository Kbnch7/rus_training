import random
import asyncio
from telebot.async_telebot import AsyncTeleBot
import sqlite3
from funcs import shuffled

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
    conn = sqlite3.connect('database.db')
    with open('words.txt', "r", encoding="utf-8") as f:
        cursor_user_id = conn.cursor()
        cursor_user_id.execute("SELECT user_id FROM users WHERE user_id = ?", (message.chat.id,))
        if len(cursor_user_id.fetchall()) == 0:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (user_id, words, testing) VALUES (?, ?, ?)",
                           (message.chat.id, str(shuffled(f.read().rstrip().split()))[2:-2], 1))
            conn.commit()
            cursor_words = conn.cursor()
            cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_answer = conn.cursor()
            cursor_answer.execute("UPDATE users SET answer = ? WHERE user_id = ?", (str(cursor_words.fetchone()[0].split("', '")[0]), message.chat.id))
            conn.commit()
            cursor_words.close()
            cursor_answer.close()
            cursor.close()
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
    cursor_answer = conn.cursor()
    cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
    await bot.send_message(message.chat.id, cursor_answer.fetchone()[0].lower())
    cursor_answer.close()
    cursor_testing = conn.cursor()
    cursor_testing.execute("SELECT testing FROM users WHERE user_id = ?", (message.chat.id,))
    if cursor_testing.fetchone()[0] == 0:
        cursor_testing.execute("UPDATE users SET testing = ? WHERE user_id = ?", (1, message.chat.id))
        conn.commit()
    cursor_testing.close()
    conn.close()


@bot.message_handler()
async def get_message(message):
    a = "', '"
    conn = sqlite3.connect('database.db')
    cursor_testing = conn.cursor()
    cursor_testing.execute("SELECT testing FROM users WHERE user_id = ?", (message.chat.id, ))
    if len(cursor_testing.fetchall()) == 0:
        await bot.send_message(message.chat.id, 'Для начала тренировки введите /start')
        return
    cursor_testing.close()
    if message.text.upper() == 'СТОП':
        try:
            cursor_first_and_correct = conn.cursor()
            cursor_first_and_correct.execute("SELECT first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_count_of_words = conn.cursor()
            cursor_count_of_words.execute("SELECT count_of_words FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_percent_of_first_and_correct = conn.cursor()
            cursor_percent_of_first_and_correct.execute("UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?", (int(cursor_first_and_correct.fetchone()[0] / cursor_count_of_words.fetchone()[0] * 100), message.chat.id))
            conn.commit()
            cursor_first_and_correct.close()
            cursor_count_of_words.close()
            cursor_percent_of_first_and_correct.close()
        except ZeroDivisionError:
            cursor_percent_of_first_and_correct = conn.cursor()
            cursor_percent_of_first_and_correct.execute("UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?", ("0", message.chat.id))
            conn.commit()
            cursor_percent_of_first_and_correct.close()
        cursor_incorrect_words_list = conn.cursor()
        cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                            (message.chat.id,))
        if len(cursor_incorrect_words_list.fetchone()[0].split("', '")) < 2:
            cursor_incorrect_words_list.execute("UPDATE users SET incorrect_words_list = ? WHERE user_id = ?",("таких не встретилось", message.chat.id))
            conn.commit()
            cursor_incorrect_words_list.close()
        cursor_errors = conn.cursor()
        cursor_errors.execute("SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_count_of_words = conn.cursor()
        cursor_count_of_words.execute("SELECT count_of_words FROM users WHERE user_id = ?",(message.chat.id,))
        cursor_first_and_correct = conn.cursor()
        cursor_first_and_correct.execute("SELECT first_and_correct FROM users WHERE user_id = ?",(message.chat.id,))
        cursor_percent_of_first_and_correct = conn.cursor()
        cursor_percent_of_first_and_correct.execute("SELECT percent_of_first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_incorrect_words_list = conn.cursor()
        cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))
        await bot.send_message(message.chat.id,
                               "Тренировка завершена!\n"
                               "~~~~~~~~~~\n"
                               "Ваши результаты:\n"
                               f"Всего уникальных слов: {cursor_count_of_words.fetchone()[0]}\n"
                               f"Всего ошибок: {cursor_errors.fetchone()[0]}\n"
                               f"Правильных ответов с 1 попытки: {cursor_first_and_correct.fetchone()[0]} ({cursor_percent_of_first_and_correct.fetchone()[0]}%)\n"
                               f"Слова, с которыми возникли трудности: {', '.join(cursor_incorrect_words_list.fetchone()[0].split(a))}\n"
                               "~~~~~~~~~~\n"
                               "Для нового сеанса введите /start"
                               )
        cursor_errors.close()
        cursor_count_of_words.close()
        cursor_first_and_correct.close()
        cursor_percent_of_first_and_correct.close()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (message.chat.id,))
        cursor.close()
        conn.commit()
        conn.close()
        return
    if message.content_type == 'text':
        cursor_train_list = conn.cursor()
        cursor_train_list.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
        if cursor_train_list.fetchone()[0].split("', '"):
            cursor_incorrect_words_list = conn.cursor()
            cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_answer = conn.cursor()
            cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
            if cursor_answer.fetchone()[0] not in cursor_incorrect_words_list.fetchone()[0].split("', '"):
                cursor_incorrect_words_list.close()
                cursor_answer.close()
                cursor_count_of_words = conn.cursor()
                cursor_count_of_words.execute("UPDATE users SET count_of_words = count_of_words + 1 WHERE user_id = ?", (message.chat.id,))
                conn.commit()
                cursor_count_of_words.close()
            cursor_answer = conn.cursor()
            cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_answer1 = conn.cursor()
            cursor_answer1.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
            if message.text[1:] == cursor_answer.fetchone()[0][1:] and message.text[0].lower() == cursor_answer1.fetchone()[0][0].lower():
                cursor_answer.close()
                cursor_answer1.close()
                cursor_words = conn.cursor()
                cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_words1 = conn.cursor()
                cursor_words1.execute("UPDATE users SET words = ? WHERE user_id = ?", (str(cursor_words.fetchone()[0].split("', '")[1:])[2:-2], message.chat.id))
                conn.commit()
                cursor_words1.close()
                cursor_words.close()
                await bot.send_message(message.chat.id, "Верно!")
                cursor_answer = conn.cursor()
                cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_incorrect_words_list = conn.cursor()
                cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))
                if cursor_answer.fetchone()[0] not in cursor_incorrect_words_list.fetchone()[0].split("', '"):
                    cursor_answer.close()
                    cursor_first_and_correct = conn.cursor()
                    cursor_first_and_correct.execute("UPDATE users SET first_and_correct = first_and_correct + 1 WHERE user_id = ?", (message.chat.id,))
                    conn.commit()
                    cursor_answer.close()
                cursor_incorrect_words_list.close()
                cursor_words = conn.cursor()
                cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                if cursor_words.fetchone()[0].split("', '")[0] != '':
                    cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                    cursor_answer = conn.cursor()
                    cursor_answer.execute("UPDATE users SET answer = ? WHERE user_id = ?", (cursor_words.fetchone()[0].split("', '")[0], message.chat.id))
                    conn.commit()
                    cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id, ))
                    await bot.send_message(message.chat.id, cursor_answer.fetchone()[0].lower())
                    cursor_answer.close()

                else:
                    try:
                        cursor_first_and_correct = conn.cursor()
                        cursor_first_and_correct.execute("SELECT first_and_correct FROM users WHERE user_id = ?",
                                                         (message.chat.id,))
                        cursor_count_of_words = conn.cursor()
                        cursor_count_of_words.execute("SELECT count_of_words FROM users WHERE user_id = ?",
                                                      (message.chat.id,))
                        cursor_percent_of_first_and_correct = conn.cursor()
                        cursor_percent_of_first_and_correct.execute(
                            "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?", (
                            int(cursor_first_and_correct.fetchone()[0] / cursor_count_of_words.fetchone()[0] * 100),
                            message.chat.id))
                        conn.commit()
                        cursor_first_and_correct.close()
                        cursor_count_of_words.close()
                        cursor_percent_of_first_and_correct.close()
                    except ZeroDivisionError:
                        cursor_percent_of_first_and_correct = conn.cursor()
                        cursor_percent_of_first_and_correct.execute(
                            "UPDATE users SET percent_of_first_and_correct = ? WHERE user_id = ?", (0, message.chat.id))
                        conn.commit()
                        cursor_percent_of_first_and_correct.close()
                    cursor_incorrect_words_list = conn.cursor()
                    cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                                        (message.chat.id,))
                    if len(cursor_incorrect_words_list.fetchone()[0].split("', '")) < 2:
                        cursor_incorrect_words_list.execute(
                            "UPDATE users SET incorrect_words_list = ? WHERE user_id = ?",
                            ("таких не встретилось", message.chat.id))
                        conn.commit()
                        cursor_incorrect_words_list.close()
                    cursor_errors = conn.cursor()
                    cursor_errors.execute("SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))
                    cursor_count_of_words = conn.cursor()
                    cursor_count_of_words.execute("SELECT count_of_words FROM users WHERE user_id = ?",
                                                  (message.chat.id,))
                    cursor_first_and_correct = conn.cursor()
                    cursor_first_and_correct.execute("SELECT first_and_correct FROM users WHERE user_id = ?",
                                                     (message.chat.id,))
                    cursor_percent_of_first_and_correct = conn.cursor()
                    cursor_percent_of_first_and_correct.execute(
                        "SELECT percent_of_first_and_correct FROM users WHERE user_id = ?", (message.chat.id,))
                    cursor_incorrect_words_list = conn.cursor()
                    cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                                        (message.chat.id,))
                    await bot.send_message(message.chat.id,
                                           "Тренировка завершена!\n"
                                           "~~~~~~~~~~\n"
                                           "Ваши результаты:\n"
                                           f"Всего уникальных слов: {cursor_count_of_words.fetchone()[0]}\n"
                                           f"Всего ошибок: {cursor_errors.fetchone()[0]}\n"
                                           f"Правильных ответов с 1 попытки: {cursor_first_and_correct.fetchone()[0]}({cursor_percent_of_first_and_correct.fetchone()[0]}%)\n"
                                           f"Слова, с которыми возникли трудности: {', '.join(cursor_incorrect_words_list.fetchone()[0].split(a))}\n"
                                           "~~~~~~~~~~\n"
                                           "Для нового сеанса введите /start"
                                           )
                    cursor_errors.close()
                    cursor_count_of_words.close()
                    cursor_first_and_correct.close()
                    cursor_percent_of_first_and_correct.close()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE user_id = ?", (message.chat.id,))
                    cursor.close()
                    conn.commit()
                    conn.close()
                    return
            else:
                cursor_answer = conn.cursor()
                cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_incorrect_words_list = conn.cursor()
                cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_errors = conn.cursor()
                cursor_errors.execute("SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_words = conn.cursor()
                cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                await bot.send_message(message.chat.id, f"Неверно, слово {cursor_answer.fetchone()[0].split(a)[0]} попадется вам еще раз!")
                cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
                if cursor_answer.fetchone()[0] not in cursor_incorrect_words_list.fetchone()[0].split("', '"):
                    cursor_incorrect_words_list1 = conn.cursor()
                    cursor_incorrect_words_list1.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                                        (message.chat.id,))
                    cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
                    #print(str(cursor_answer.fetchone()[0]))
                    #print(str(cursor_incorrect_words_list1.fetchone()[0]))

                    cursor_incorrect_words_list.execute("UPDATE users SET incorrect_words_list = ?", (str(cursor_answer.fetchone()[0])+ "', '" + str(cursor_incorrect_words_list1.fetchone()[0]), ))
                    conn.commit()
                    cursor_incorrect_words_list1.close()
                cursor_answer.close()
                cursor_incorrect_words_list.close()
                cursor_errors = conn.cursor()
                cursor_errors.execute("UPDATE users SET errors = errors + 1")
                conn.commit()
                cursor_errors.close()
                cursor_words = conn.cursor()
                cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_words1 = conn.cursor()
                cursor_words1.execute("UPDATE users SET words = ? WHERE user_id = ?", (str(shuffled(cursor_words.fetchone()[0].split("', '")))[2:-2], message.chat.id))
                conn.commit()
                cursor_words1.close()
                cursor_words = conn.cursor()
                cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
                cursor_answer = conn.cursor()
                cursor_answer.execute("UPDATE users SET answer = ? WHERE user_id = ?", (cursor_words.fetchone()[0].split("', '")[0], message.chat.id))
                conn.commit()
                cursor_words.close()
                cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
                await bot.send_message(message.chat.id, cursor_answer.fetchone()[0].lower())
                cursor_answer.close()
                return
    else:
        cursor_answer = conn.cursor()
        cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_incorrect_words_list = conn.cursor()
        cursor_incorrect_words_list.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                            (message.chat.id,))
        cursor_errors = conn.cursor()
        cursor_errors.execute("SELECT errors FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_words = conn.cursor()
        cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
        await bot.send_message(message.chat.id,
                               f"Неверно, слово {cursor_answer.fetchone()[0].split(a)[0]} попадется вам еще раз!")
        cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
        if cursor_answer.fetchone()[0] not in cursor_incorrect_words_list.fetchone()[0].split("', '"):
            cursor_incorrect_words_list1 = conn.cursor()
            cursor_incorrect_words_list1.execute("SELECT incorrect_words_list FROM users WHERE user_id = ?",
                                                 (message.chat.id,))
            cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
            cursor_incorrect_words_list.execute("UPDATE users SET incorrect_words_list = ?", (
            str(cursor_answer.fetchone()[0])+ "', '" + str(cursor_incorrect_words_list1.fetchone()[0])[2:-2],))
            conn.commit()
            cursor_incorrect_words_list1.close()
        cursor_answer.close()
        cursor_incorrect_words_list.close()
        cursor_errors = conn.cursor()
        cursor_errors.execute("UPDATE users SET errors = errors + 1")
        conn.commit()
        cursor_errors.close()
        cursor_words = conn.cursor()
        cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_words1 = conn.cursor()
        cursor_words1.execute("UPDATE users SET words = ? WHERE user_id = ?",
                              (str(shuffled(cursor_words.fetchone()[0].split("', '")))[2:-2], message.chat.id))
        conn.commit()
        cursor_words1.close()
        cursor_words = conn.cursor()
        cursor_words.execute("SELECT words FROM users WHERE user_id = ?", (message.chat.id,))
        cursor_answer = conn.cursor()
        cursor_answer.execute("UPDATE users SET answer = ? WHERE user_id = ?",
                              (cursor_words.fetchone()[0].split("', '")[0], message.chat.id))
        conn.commit()
        cursor_words.close()
        cursor_answer.execute("SELECT answer FROM users WHERE user_id = ?", (message.chat.id,))
        await bot.send_message(message.chat.id, cursor_answer.fetchone()[0].lower())
        cursor_answer.close()
        return



async def main():
    await bot.infinity_polling(timeout=1000)
try:
    if __name__ == "__main__":
        asyncio.run(main())
except TimeoutError as e:
    print(e)
    if __name__ == "__main__":
        asyncio.run(main())