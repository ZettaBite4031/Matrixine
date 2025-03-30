from bot import MatrixineBot, Config


def main():
    config = Config()
    bot = MatrixineBot(config)
    bot.run()


if __name__ == "__main__":
    main()
