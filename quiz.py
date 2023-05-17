import json
import random
import os
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import ParseMode
import textwrap

nltk.download('stopwords') # Download stopwords resource

WUP_Threshold = 0.8
greeting = ['Hi there, how are you doing today!\nI am quizzy, let\'s play a quiz today!', 'Hi I\'m quizzy, your quizmaster!', 'Quizzy here, let\'s start']
wrong_category = ['Hmm! We currently do not have any quizzes on that.', 'Sorry we don\'t have any questions regarding that.', 'Hmm, pick another one!']
next_question = ['Here comes the next question!', 'Get ready for the next one!', 'Here comes another']
correct_answer = ['Correct answer, well done!', 'You\'re smart!', 'You\'re a genius']
wrong_answer = ['Sorry, wrong answer. Nevermind', 'Wrong! Buck up', 'Nah! Come on!']

def extractNounsAndAdjectives(words):
    NJ = []
    pos = nltk.pos_tag(words)
    for word, tag in pos:
        if tag[0] in ('N', 'J'):
            NJ.append(word)
    return NJ


# Wu-Palmer similarity
def WUPSimilarity(w1, w2):
    w1 = wn.synsets(w1)
    w2 = wn.synsets(w2)
    max_WUP = 0
    # Checking for the first 3 synonyms in order to avoid noise
    for i in range(0, min(3, len(w1))):
        for j in range(0, min(3, len(w2))):
            sim = w1[i].wup_similarity(w2[j])
            if sim is not None:
                max_WUP = max(max_WUP, sim)
    return max_WUP


# Compute possible categories based on user response
def computeCategories(categories, user_response_NJ):
    probable_categories = {}
    for w1 in categories:
        for w2 in user_response_NJ:
            for w in w1.split('-'):
                sim = WUPSimilarity(w, w2)
                if sim >= 1:
                    probable_categories.clear()
                    probable_categories[w1] = w2
                    return probable_categories
                elif sim >= WUP_Threshold:
                    probable_categories[w1] = w2
    return probable_categories


# Compute the possible choices present in user_response
def computeChoices(user_response, choices):
    punctuations = list(string.punctuation)
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    ct = 'a'
    probable_choices = []
    user_response = nltk.word_tokenize(user_response.lower())
    user_response = [lemmatizer.lemmatize(word, pos='v') for word in user_response]
    user_response = [i for i in user_response if i not in punctuations and i not in stop_words]
    user_response = set(user_response)
    for choice in choices:
        choice = nltk.word_tokenize(choice.lower())
        choice = [lemmatizer.lemmatize(word, pos='v') for word in choice]
        choice = [i for i in choice if i not in punctuations and i not in stop_words]
        choice = set(choice)
        if len(user_response.intersection(choice)) > 0:
            probable_choices.append(ct)
        ct = chr(ord(ct) + 1)
    return probable_choices


def displayBotResponse(score, responses, isCorrect, answer_choice=''):
    response = random.choice(responses)
    if isCorrect:
        score += 1
    else:
        score -= 0.25
        response += "\nThe correct answer is {}".format(answer_choice.upper())
    response += '\nScore = {:.2f}'.format(score)
    return response, score


def get_quiz_question(category, previous_questions):
    with open(os.path.join('json question file folder', category + '.json'), 'r') as f:
        quiz_data = json.load(f)
    quiz_questions = quiz_data['quiz_questions']
    for question in quiz_questions:
        if question['question'] not in previous_questions:
            return question
    return None


def quiz(update, context):
    if 'quiz_score' not in context.chat_data:
        context.chat_data['quiz_score'] = 0
    if 'previous_questions' not in context.chat_data:
        context.chat_data['previous_questions'] = []
    if 'quiz_category' not in context.chat_data:
        context.chat_data['quiz_category'] = ''
    if context.args:
        categories = context.args
        category = ' '.join(categories)
        probable_categories = computeCategories(quiz_data['quiz_categories'], extractNounsAndAdjectives(categories))
        if len(probable_categories) > 0:
            category = list(probable_categories.keys())[0]
        else:
            category = ''
        context.chat_data['quiz_category'] = category
    else:
        category = context.chat_data['quiz_category']
    if category == '':
        context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(wrong_category))
        return
    quiz_question = get_quiz_question(category, context.chat_data['previous_questions'])
    if quiz_question:
        context.chat_data['previous_questions'].append(quiz_question['question'])
        response_options = quiz_question['options']
        answer_choice = quiz_question['answer']
        context.chat_data['quiz_correct_choice'] = answer_choice
        random.shuffle(response_options)
        response_options.append('I don\'t know')
        quiz_question_text = quiz_question['question'] + '\n'
        for i in range(len(response_options)):
            quiz_question_text += '{}. {}\n'.format(chr(ord('a') + i), response_options[i])
        quiz_question_text += '\nPlease type in the letter corresponding to your choice (a, b, c, d, e)'
        context.chat_data['quiz_question'] = quiz_question_text
        context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(next_question))
        text = textwrap.wrap(quiz_question_text, width=400)
        for line in text:
            context.bot.send_message(chat_id=update.effective_chat.id, text=line)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That\'s all the questions for now. Your final score is {:.2f}'.format(
            context.chat_data['quiz_score']))
        context.chat_data['quiz_score'] = 0
        context.chat_data['previous_questions'] = []
        context.chat_data['quiz_category'] = ''


def quiz_answer(update, context):
    if 'quiz_score' not in context.chat_data:
        context.chat_data['quiz_score'] = 0
    if 'previous_questions' not in context.chat_data:
        context.chat_data['previous_questions'] = []
    if 'quiz_category' not in context.chat_data:
        context.chat_data['quiz_category'] = ''
    if 'quiz_question' not in context.chat_data:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please start the quiz with /quiz')
        return
    user_response = update.message.text.lower()
    answer_choice = context.chat_data['quiz_correct_choice']
    if user_response == answer_choice.lower():
        is_correct = True
        response, context.chat_data['quiz_score'] = displayBotResponse(context.chat_data['quiz_score'], correct_answer, True)
    elif user_response in computeChoices(user_response, context.chat_data['quiz_question']):
        is_correct = False
        response, context.chat_data['quiz_score'] = displayBotResponse(context.chat_data['quiz_score'], wrong_answer, False, answer_choice)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Invalid choice. Please select a valid option')
        return
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    quiz(update, context)


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(greeting))


def main():
    # Set up the bot
    updater = Updater(token='YOUR_TOKEN_HERE', use_context=True)
    dispatcher = updater.dispatcher

    # Add handlers for start command and quiz command
    start_handler = CommandHandler('start', start)
    quiz_handler = CommandHandler('quiz', quiz)
    quiz_answer_handler = MessageHandler(Filters.text & ~Filters.command, quiz_answer)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(quiz_handler)
    dispatcher.add_handler(quiz_answer_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
