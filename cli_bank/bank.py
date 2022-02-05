from cmd import Cmd
from models import User, Ledger, Session, engine

# Due to choosing of Cmd lib for cli app, it was easier to write
# a parser than to use argparse lib
class ArgParser:

    @staticmethod
    def parse_args(args: str, function_name: str, args_amount: int = 3) -> list | None:
        res = []

        if function_name == "deposit" or function_name == "withdraw":
            arg1 = '--client="'
            arg2 = '" --amount='
            arg3 = ' --description="'
        elif function_name == "show_bank_statement":
            arg1 = '--client="'
            arg2 = '" --since="'
            arg3 = '" --till="'

        client_str_start_quote_idx = args.find(arg1)
        client_str_end_quote_idx = args.find(arg2)
        if client_str_start_quote_idx == 0 and client_str_end_quote_idx != -1:
            name_idx_start = len(arg1)
            client_name = args[name_idx_start:client_str_end_quote_idx]
            res.append(client_name)
        else:
            return None

        amount_str_start_idx = client_str_end_quote_idx + \
            len(arg2)
        amount_str_end_idx = args.find(arg3)
        if amount_str_end_idx > amount_str_start_idx:
            amount = args[amount_str_start_idx:amount_str_end_idx]
            res.append(amount)
        else:
            return None

        description_str_start_idx = amount_str_end_idx + \
            len(arg3)
        description_str_end_idx = -1
        if args[-1] != '"':
            return None

        description = args[description_str_start_idx:description_str_end_idx]
        if description == "":
            return None
        res.append(description)

        if function_name == "deposit" or function_name == "withdraw":

            # erasing quotes around amount if they were provided mistakenly
            amount_str = res[1]
            prepared_amount_str = amount_str.replace('"', '')

            # and checking if the number is convertable to float
            try:
                float(prepared_amount_str)
            except:
                return None

            res[1] = prepared_amount_str

        return res


# Some functions that weren't stated in the task were made only for my testing. Don't draw your attention to them.
class MyCmd(Cmd):
    prompt = "> "

    def do_help(self, args):
        print("Create a client: create <name> <money_amount>\nExample: create John Dillinger 30000\n")
        print('deposit --client="<client_name>" --amount=<money_amount> --description="<description>"\n')
        print('withdraw --client="<client_name>" --amount=<money_amount> --description="<description>"\n')
        print('show_bank_statement --client="<client_name>" --since="<YYYY-MM-DD HH:MM:SS>" --till="<YYYY-MM-DD HH:MM:SS>"\n')
        print("Exit: exit\n")
        print("Take into account that the program is expecting client names to be unique.")


    def do_create(self, args):
        """Create a client with any amount of money on start."""
        try:
            name, money_amount = args.rsplit(" ", 1)
            money_amount = float(money_amount)
        except ValueError:
            print("Please enter name and money amount separated with whitespace.")
            return
        except:
            print("Unexpected error on parsing the input.")
            return

        if money_amount < 0:
            print("Money amount can not be less than 0.")
            return

        created_user = User(name=name, balance=money_amount)
        with Session(engine) as session:
            session.begin()
            session.add(created_user)
            session.commit()

        print('Created account. Client`s name: "{}", Client`s money: ${}'
              .format(name, money_amount))
        return


    def do_get_all_clients(self, args):
        with Session(engine) as session:
            objects = session.query(User).all()
            for obj in objects:
                print(obj.name, "$" + str(obj.balance))


    def do_get_client(self, client_name):
        with Session(engine) as session:
            objects = session.query(User).filter_by(name=client_name)
            for obj in objects:
                print(obj.name, "$" + str(obj.balance))


    def do_deposit(self, args):
        wrong_usage_msg = 'Wrong arguments.\nUsage: deposit --client="<yourtext>" --amount="<yourtext>" --description="<yourtext>"'

        list_of_items = ArgParser.parse_args(args, "deposit")
        if list_of_items == None or len(list_of_items) != 3:
            print(wrong_usage_msg)
            return

        client_name = list_of_items[0]
        amount = list_of_items[1]
        description = list_of_items[2]

        amount = float(amount)
        if amount <= 0:
            if amount == 0:
                print("Use a non-zero amount of money for a transaction.")
            else:
                print("You can not deposit a negative amount of money. Use withdraw function instead.")
            return

        with Session(engine) as session:
            session.begin()
            try:
                user = session.query(User).with_for_update()\
                    .filter_by(name=client_name)\
                    .one_or_none()
                if user == None:
                    print('User with name: "{}" was not found or several users were found.'
                          .format(client_name))
                    return
                prev_balance = user.balance
                # This code should be safe for race condition
                # because of with_for_update() lock used above
                user.balance += amount
                curr_balance = user.balance

                entry = Ledger(
                    recepient_id=user.id,
                    description=description,
                    previous_balance=prev_balance,
                    current_balance=curr_balance
                )
                session.add(entry)
            except Exception as e:
                session.rollback()
                print("Error on deposit:", e)
                raise
            else:
                session.commit()

        print("Deposit succesful! Name: {}, current balance: ${}"
              .format(client_name, curr_balance))


    def do_withdraw(self, args):
        wrong_usage_msg = 'Wrong arguments.\nUsage: withdraw --client="<yourtext>" --amount=<yourtext> --description="<yourtext>"'

        list_of_items = ArgParser.parse_args(args, "withdraw")
        if list_of_items == None or len(list_of_items) != 3:
            print(wrong_usage_msg)
            return
        client_name = list_of_items[0]
        amount = list_of_items[1]
        description = list_of_items[2]

        amount = float(amount)
        if amount <= 0:
            if amount == 0:
                print("Use a non-zero amount of money for a transaction.")
            else:
                print(
                    "You can not withdraw negative amount of money.\nTo send money, use deposit function.")
            return

        with Session(engine) as session:
            session.begin()
            try:
                user = session.query(User).with_for_update()\
                    .filter_by(name=client_name)\
                    .one_or_none()
                if user == None:
                    print('User with name: "{}" was not found or several users were found.'
                          .format(client_name))
                    return
                prev_balance = user.balance
                if prev_balance - amount < 0:
                    print(
                        "Withdrawal can not be performed: client does not have enough money.")
                    return
                # This code should be safe for race condition
                # because of with_for_update() lock used above
                user.balance -= amount
                curr_balance = user.balance

                entry = Ledger(
                    recepient_id=user.id,
                    description=description,
                    previous_balance=prev_balance,
                    current_balance=curr_balance
                )
                session.add(entry)
            except Exception as e:
                session.rollback()
                print("Error on withdrawal:", e)
                raise
            else:
                session.commit()

        print('Withdrawal successful! Name: "{}", current balance: {}'
              .format(client_name, curr_balance))


    def do_get_entry_by_id(self, id):
        with Session(engine) as session:
            entry = session.get(Ledger, id)
            if entry == None:
                print("Error: couldn't find entry by id.")
                return
            print("entry id: {}\nrecepient id: {}\noperation date: {}\
\ndescription:{}\nprev balance: {}\ncurrent balance: {}\nuser name: {}".format(entry.id,
                                                                               entry.recepient_id,
                                                                               entry.operation_date,
                                                                               entry.description,
                                                                               entry.previous_balance,
                                                                               entry.current_balance,
                                                                               entry.recepient.name))
                
        
    def do_show_bank_statement(self, args):
        wrong_usage_msg = 'Wrong arguments.\nUsage: show_bank_statement --client="<yourtext>" --since="<date_whitespace_time>" \
--till="<date_whitespace_time>" \nExample: --client="John Dillinger" --since="2022-01-31 13:00:00" -till="2022-02-01 14:00:00"'

        list_of_items = ArgParser.parse_args(args, "show_bank_statement")
        
        if list_of_items == None or len(list_of_items) != 3:
            print(wrong_usage_msg)
            return
        
        client_name = list_of_items[0]
        since = list_of_items[1]
        till = list_of_items[2]
        
        
        with Session(engine) as session:
            entries = session.query(Ledger).join(User)\
                .filter(
                User.name == client_name,
                Ledger.operation_date >= since,
                Ledger.operation_date <= till
            )
            
            print('| Date\t\t      | Description   | Withdrawals | Deposits | Balance |\n')
            
            total_withdrawals = 0
            total_deposits = 0
            total_balance = 0
            for entry in entries:
                
                operation = entry.current_balance - entry.previous_balance
                if operation < 0:
                    total_withdrawals += -(operation)
                    withdrawal = "$" + str(-(operation))
                    deposit = "\t" # Just for table formatting
                else:
                    withdrawal = ""
                    total_deposits += operation
                    deposit = "$" + str(operation)
                    
                entry_description_formatted = entry.description[0:10] + "..."
                
                print('| {} | {} | {}\t | {}\t | ${} |'
                      .format(entry.operation_date,
                              entry_description_formatted,
                              withdrawal,
                              deposit,
                              entry.current_balance))
                total_balance = entry.current_balance
                
            total_withdrawals_formatted = ""
            total_deposits_formatted = ""
            if total_withdrawals != 0:
                total_withdrawals_formatted = "$" + str(total_withdrawals)
            if total_deposits != 0:
                total_deposits_formatted = "$" + str(total_deposits)
            print('| {}\t\t\t      | {}\t | {}\t | ${} |'
                  .format('Totals', 
                          total_withdrawals_formatted, 
                          total_deposits_formatted,
                          total_balance))
        

    def do_exit(self, args):
        print("Thank you and goodbye!")
        return True


if __name__ == "__main__":

    app = MyCmd()
    app.cmdloop("Service started! Type help to list commands.")
    