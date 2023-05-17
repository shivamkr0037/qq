import json
import os
import random
import nltk
from nltk.corpus import wordnet
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import string
import logging

# Load nltk data
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

# Messages
next_question = ['Next Question:', 'Next one:', 'Here is the next question:', 'Moving on:', 'Next up:']
correct_answer = 'Correct!'
wrong_answer = 'Wrong answer :('
wrong_category = ['Sorry, that category is not available.', 'I\'m sorry, I don\'t have that category.', 'That category doesn\'t exist.']

# Load categories
def loadAllCategories():
    with open('./OpenTriviaQA_JSON/categories.json') as f:
        data = json.load(f)
    return data

# Load questions for a category
def loadQuestions(category):
    if category is None:
        return None
    with open('./OpenTriviaQA_JSON/{}.json'.format(category)) as f:
        data = json.load(f)
    questions = []
    for q in data:
        question = {
            'question': q['question'],
            'category': q['category'],
            'answer': q['answer'],
            'choices': q['choices']
        }
        questions.append(question)
    return questions

# Extract nouns and adjectives from a sentence
def extractNounsAndAdjectives(tokens):
    tagged = nltk.pos_tag(tokens)
    nouns_adj = [word for word, pos in tagged if (pos == 'NN' or pos == 'NNS' or pos == 'NNP' or pos == 'JJ')]
    return set(nouns_adj)

# Compute categories based on a set of nouns and adjectives
def computeCategories(categories, nouns_adj):
    probable_categories = [c for c in categories if len(nouns_adj.intersection(set(loadQuestions(c)[0]['question'].split()))) > 0]
    return probable_categories

# Compute the choices for a question
def computeChoices(question, choices):
    probable_choices = [c for c in choices if len(set(nltk.word_tokenize(question.lower())).intersection(set(nltk.word_tokenize(c.lower())))) > 0]
    return probable_choices

# Display the bot response for a question
def displayBotResponse(score, correct_answer, isCorrect, correct_choice):
    response = ''
    if isCorrect:
        score += 1
        response += '{} Your answer is correct! The correct answer is {}.\n\n'.format(correct_answer, correct_choice)
    else:
        response += '{} The correct answer is {}.\n\n'.format(correct_answer, correct_choice)
    response += 'Your score is: {}/{}\n\n'.format(score, i+1)
    return score, response

# Quiz function
def quiz(update, context):
    categories = loadAllCategories()
    user_response = update.message.text
    if 'categories' in user_response.lower():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Here are the categories available:\n{}".format('\n'.join(categories)))
        return
    if 'help' in user_response.lower():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Type 'categories' to view all available categories, and type 'quiz /category' to start a quiz in that category")
        return
    category = user_response.split('/')
    if len(category) < 2:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please enter a valid category. Type \'help\' for help')
        return
    category = category[1]
    questions = loadQuestions(category)
    if questions is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text=random.choice(wrong_category))
        return
    score, response = 0, ''
    for i, question in enumerate(questions):
        response += random.choice(next_question) + '\n\n'
        response += question['question'] + '\n'
        choices = question['choices']
        correct_choice = question['answer']
        choices.append(correct_choice)
        random.shuffle(choices)
        response += '\n'.join(computeChoices(question['question'], choices)) + '\n'
        user_response = update.message.text
        user_response_NJ = extractNounsAndAdjectives(nltk.word_tokenize(user_response))
        probable_categories = computeCategories(set([category]), user_response_NJ)
        probable_choices = computeChoices(user_response, choices)
        isCorrect = False
        if correct_choice in probable_choices:
            isCorrect = True
        score, bot_response = displayBotResponse(score, correct_answer if isCorrect else wrong_answer, isCorrect, correct_choice)
        response += bot_response + '\n\n'
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Main function
def main():
    # Set up the Telegram bot
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(token='6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8', use_context=True)
    dispatcher = updater.dispatcher

    # Set up handlers for commands
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    quiz_handler = MessageHandler(Filters.text & (~Filters.command), quiz)

    # Add handlers to the dispatcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(quiz_handler)

    # Start the bot
    updater.start_polling()

# Start function
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a trivia bot! Type 'help' for help.")

# Help function
def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Type 'categories' to view all available categories, and type 'quiz /category' to start a quiz in that category")

if __name__ == '__main__':
    main()
