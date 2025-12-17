"""Interactive CLI application for Paystack operations."""

import asyncio
import sys
import uuid
import msvcrt  # Windows-specific for arrow key handling
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from app.utils.config import settings
from app.utils.logger import get_logger
from app.services.paystack_service import paystack_service, PaystackAPIError

logger = get_logger("cli_app")
console = Console()


class PaystackCLI:
    """Interactive CLI for Paystack operations."""
    
    def __init__(self):
        self.running = True
        self.banks_cache = {}
        self.recipients_cache = []
    
    def display_header(self):
        """Display application header."""
        header = Panel(
            Text(f"{settings.app_name} v{settings.app_version}", justify="center", style="bold blue"),
            box=box.DOUBLE,
            style="blue"
        )
        console.print(header)
        console.print()
    
    def display_error(self, message: str):
        """Display error message."""
        console.print(f"[bold red]Error:[/bold red] {message}")
        console.print()
    
    def display_success(self, message: str):
        """Display success message."""
        console.print(f"[bold green]Success:[/bold green] {message}")
        console.print()
    
    def display_info(self, message: str):
        """Display info message."""
        console.print(f"[bold blue]Info:[/bold blue] {message}")
        console.print()
    
    def get_user_input(self, message: str, default: str = "") -> str:
        """Get user input with optional default."""
        if default:
            return input(f"{message} [{default}]: ").strip() or default
        return input(f"{message}: ").strip()
    
    def confirm_action(self, message: str) -> bool:
        """Get user confirmation."""
        while True:
            choice = input(f"{message} (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                console.print("[red]Please enter 'y' or 'n'[/red]")
    
    async def resolve_bank_account(self):
        """Resolve bank account details by account number and bank code."""
        console.print("[bold cyan]🏦 Resolve Bank Account[/bold cyan]")
        console.print()
        
        try:
            currency = settings.default_currency  # Always use NGN
            
            # Fetch banks if not cached
            if currency not in self.banks_cache:
                console.print("Fetching banks...")
                banks = await paystack_service.list_banks(currency)
                self.banks_cache[currency] = {bank['code']: bank for bank in banks}
            
            # Display available banks
            banks = self.banks_cache[currency]
            if not banks:
                self.display_error(f"No banks found for currency {currency}")
                return
            
            # Show available banks with numbered selection
            console.print("\n[bold]Available Banks:[/bold]")
            bank_list = list(banks.values())
            
            # Display banks in a numbered list (show first 20 for readability)
            display_count = min(20, len(bank_list))
            for i, bank in enumerate(bank_list[:display_count], 1):
                console.print(f"  {i:2d}. {bank['name']} ({bank['code']})")
            
            if len(bank_list) > display_count:
                console.print(f"  ... and {len(bank_list) - display_count} more banks")
                console.print("  [dim]Type the bank number or name[/dim]")
            
            # Get bank selection
            bank_input = self.get_user_input("Enter bank number or search bank name")
            
            selected_bank = None
            try:
                # Try to parse as number first
                bank_index = int(bank_input) - 1
                if 0 <= bank_index < len(bank_list):
                    selected_bank = bank_list[bank_index]
            except ValueError:
                # Search by name if not a number
                search_term = bank_input.lower()
                for bank in bank_list:
                    if search_term in bank['name'].lower():
                        selected_bank = bank
                        break
            
            if not selected_bank:
                self.display_error("Bank not found. Please try again.")
                return
            
            bank_code = selected_bank['code']
            console.print(f"Selected: {selected_bank['name']} ({bank_code})")
            
            # Get account details
            account_number = self.get_user_input("Account Number")
            
            if not account_number:
                self.display_error("Account number is required")
                return
            
            console.print("Resolving account...")
            account_info = await paystack_service.resolve_account(account_number, bank_code)
            
            # Display result
            bank_name = banks[bank_code]['name']
            console.print()
            console.print(Panel(
                f"[bold]Account Details:[/bold]\n\n"
                f"Account Number: {account_info['account_number']}\n"
                f"Account Name: {account_info['account_name']}\n"
                f"Bank: {bank_name}",
                title="✅ Account Resolved",
                title_align="left",
                border_style="green"
            ))
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to resolve account: {e.message}")
        except Exception as e:
            logger.error(f"Error resolving account: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def create_recipient(self):
        """Create a new transfer recipient."""
        console.print("[bold cyan]👤 Create Transfer Recipient[/bold cyan]")
        console.print()
        
        try:
            # Get recipient details
            name = self.get_user_input("Recipient Name")
            currency = settings.default_currency  # Always use NGN
            
            # Fetch banks if not cached
            if currency not in self.banks_cache:
                console.print("Fetching banks...")
                banks = await paystack_service.list_banks(currency)
                self.banks_cache[currency] = {bank['code']: bank for bank in banks}
            
            banks = self.banks_cache[currency]
            if not banks:
                self.display_error(f"No banks found for currency {currency}")
                return
            
            # Show available banks with numbered selection
            console.print("\n[bold]Available Banks:[/bold]")
            bank_list = list(banks.values())
            
            # Display banks in a numbered list (show first 20 for readability)
            display_count = min(20, len(bank_list))
            for i, bank in enumerate(bank_list[:display_count], 1):
                console.print(f"  {i:2d}. {bank['name']} ({bank['code']})")
            
            if len(bank_list) > display_count:
                console.print(f"  ... and {len(bank_list) - display_count} more banks")
                console.print("  [dim]Type the bank number or name[/dim]")
            
            # Get bank selection
            bank_input = self.get_user_input("Enter bank number or search bank name")
            
            selected_bank = None
            try:
                # Try to parse as number first
                bank_index = int(bank_input) - 1
                if 0 <= bank_index < len(bank_list):
                    selected_bank = bank_list[bank_index]
            except ValueError:
                # Search by name if not a number
                search_term = bank_input.lower()
                for bank in bank_list:
                    if search_term in bank['name'].lower():
                        selected_bank = bank
                        break
            
            if not selected_bank:
                self.display_error("Bank not found. Please try again.")
                return
            
            bank_code = selected_bank['code']
            console.print(f"Selected: {selected_bank['name']} ({bank_code})")
            
            account_number = self.get_user_input("Account Number")
            description = self.get_user_input("Description (optional)", "")
            
            if not all([name, account_number]):
                self.display_error("Name and account number are required")
                return
            
            # Resolve account first
            console.print("Verifying account...")
            try:
                account_info = await paystack_service.resolve_account(account_number, bank_code)
                console.print(f"Account belongs to: {account_info['account_name']}")
                
                if not self.confirm_action("Create recipient with this account?"):
                    return
            except PaystackAPIError:
                console.print("[yellow]Warning: Could not verify account. Continue anyway?[/yellow]")
                if not self.confirm_action("Continue without verification?"):
                    return
            
            # Create recipient
            console.print("Creating recipient...")
            recipient = await paystack_service.create_transfer_recipient(
                recipient_type="nuban",
                name=name,
                account_number=account_number,
                bank_code=bank_code,
                currency=currency,
                description=description or ""
            )
            
            # Clear recipients cache
            self.recipients_cache = []
            
            console.print()
            console.print(Panel(
                f"[bold]Recipient Created:[/bold]\n\n"
                f"Name: {recipient['name']}\n"
                f"Code: {recipient['recipient_code']}\n"
                f"Account: {recipient['details']['account_number']}\n"
                f"Bank: {recipient['details']['bank_name']}",
                title="✅ Recipient Created",
                title_align="left",
                border_style="green"
            ))
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to create recipient: {e.message}")
        except Exception as e:
            logger.error(f"Error creating recipient: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def check_balance(self):
        """Check account balance."""
        console.print("[bold cyan]💰 Check Balance[/bold cyan]")
        console.print()
        
        try:
            balances = await paystack_service.get_balance()
            
            if not balances:
                self.display_info("No balance information available")
                return
            
            table = Table(title="Account Balances")
            table.add_column("Currency", style="cyan")
            table.add_column("Balance", style="green", justify="right")
            table.add_column("Formatted", style="white", justify="right")
            
            for balance in balances:
                currency = balance['currency']
                amount = balance['balance']
                formatted = settings.format_amount(amount, currency)
                
                table.add_row(
                    currency,
                    str(amount),
                    formatted
                )
            
            console.print(table)
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to fetch balance: {e.message}")
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def list_transfers(self):
        """List recent transfers."""
        console.print("[bold cyan]📤 My Outgoing Transfers (Money I Sent)[/bold cyan]")
        console.print()
        
        try:
            response = await paystack_service.list_transfers(per_page=10)
            transfers = response.get('data', [])
            
            if not transfers:
                self.display_info("No outgoing transfers found - you haven't sent any money yet")
                return
            
            table = Table(title="My Outgoing Transfers")
            table.add_column("Date", style="cyan")
            table.add_column("Recipient", style="white")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Status", style="yellow")
            table.add_column("Reason", style="dim")
            
            for transfer in transfers:
                date = transfer['createdAt'][:10]  # Extract date
                recipient_name = transfer.get('recipient', {}).get('name', 'Unknown')
                amount = settings.format_amount(transfer['amount'], transfer['currency'])
                status = transfer['status']
                reason = transfer.get('reason', '')[:30] + '...' if len(transfer.get('reason', '')) > 30 else transfer.get('reason', '')
                
                table.add_row(date, recipient_name, amount, status, reason)
            
            console.print(table)
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to fetch transfers: {e.message}")
        except Exception as e:
            logger.error(f"Error fetching transfers: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def initiate_transfer(self):
        """Initiate a new transfer."""
        console.print("[bold cyan]💸 Initiate New Transfer[/bold cyan]")
        console.print()
        
        try:
            # Get available recipients
            if not self.recipients_cache:
                console.print("Fetching recipients...")
                response = await paystack_service.list_transfer_recipients()
                self.recipients_cache = response.get('data', [])
            
            if not self.recipients_cache:
                self.display_error("No recipients found. Please create a recipient first.")
                return
            
            # Display recipients
            console.print("[bold]Available Recipients:[/bold]")
            table = Table()
            table.add_column("Index", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Bank", style="dim")
            table.add_column("Account", style="dim")
            
            for i, recipient in enumerate(self.recipients_cache):
                table.add_row(
                    str(i + 1),
                    recipient['name'],
                    recipient['details']['bank_name'],
                    recipient['details']['account_number']
                )
            
            console.print(table)
            
            # Get recipient selection
            try:
                recipient_index = int(self.get_user_input("Select recipient (number)")) - 1
                if recipient_index < 0 or recipient_index >= len(self.recipients_cache):
                    self.display_error("Invalid recipient selection")
                    return
            except ValueError:
                self.display_error("Please enter a valid number")
                return
            
            selected_recipient = self.recipients_cache[recipient_index]
            
            # Get transfer details
            amount_str = self.get_user_input(f"Amount ({settings.default_currency})")
            reason = self.get_user_input("Transfer reason")
            
            try:
                amount_float = float(amount_str)
                amount_kobo = settings.to_subunit(amount_float)
            except ValueError:
                self.display_error("Please enter a valid amount")
                return
            
            if not reason:
                self.display_error("Transfer reason is required")
                return
            
            # Generate reference
            reference = f"TXN_{uuid.uuid4().hex[:8].upper()}"
            
            # Confirm transfer
            console.print()
            console.print(Panel(
                f"[bold]Transfer Details:[/bold]\n\n"
                f"Recipient: {selected_recipient['name']}\n"
                f"Account: {selected_recipient['details']['account_number']}\n"
                f"Bank: {selected_recipient['details']['bank_name']}\n"
                f"Amount: {settings.format_amount(amount_kobo)}\n"
                f"Reason: {reason}\n"
                f"Reference: {reference}",
                title="Confirm Transfer",
                border_style="yellow"
            ))
            
            if not self.confirm_action("Proceed with this transfer?"):
                return
            
            # Initiate transfer
            console.print("Initiating transfer...")
            transfer = await paystack_service.initiate_transfer(
                amount=amount_kobo,
                recipient_code=selected_recipient['recipient_code'],
                reason=reason,
                reference=reference
            )
            
            # Handle response
            if transfer['status'] == 'otp':
                console.print()
                self.display_info("Transfer requires OTP verification")
                transfer_code = transfer['transfer_code']
                
                console.print(f"Transfer Code: {transfer_code}")
                console.print("Please check your email/SMS for OTP")
                
                otp = self.get_user_input("Enter OTP")
                if otp:
                    console.print("Finalizing transfer...")
                    final_transfer = await paystack_service.finalize_transfer(transfer_code, otp)
                    
                    console.print()
                    console.print(Panel(
                        f"[bold]Transfer Completed:[/bold]\n\n"
                        f"Status: {final_transfer['status']}\n"
                        f"Reference: {final_transfer.get('reference', reference)}\n"
                        f"Transfer Code: {final_transfer.get('transfer_code', transfer_code)}",
                        title="✅ Transfer Finalized",
                        title_align="left",
                        border_style="green"
                    ))
            else:
                console.print()
                console.print(Panel(
                    f"[bold]Transfer Status:[/bold]\n\n"
                    f"Status: {transfer['status']}\n"
                    f"Transfer Code: {transfer['transfer_code']}\n"
                    f"Reference: {transfer.get('reference', reference)}",
                    title="Transfer Initiated",
                    border_style="blue"
                ))
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to initiate transfer: {e.message}")
        except Exception as e:
            logger.error(f"Error initiating transfer: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def finalize_transfer_menu(self):
        """Finalize a pending transfer with OTP."""
        console.print("[bold cyan]🔐 Finalize Transfer[/bold cyan]")
        console.print()
        
        try:
            transfer_code = self.get_user_input("Transfer Code")
            otp = self.get_user_input("OTP")
            
            if not transfer_code or not otp:
                self.display_error("Transfer code and OTP are required")
                return
            
            console.print("Finalizing transfer...")
            transfer = await paystack_service.finalize_transfer(transfer_code, otp)
            
            console.print()
            console.print(Panel(
                f"[bold]Transfer Finalized:[/bold]\n\n"
                f"Status: {transfer['status']}\n"
                f"Reference: {transfer.get('reference', 'N/A')}\n"
                f"Transfer Code: {transfer.get('transfer_code', transfer_code)}",
                title="✅ Transfer Complete",
                title_align="left",
                border_style="green"
            ))
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to finalize transfer: {e.message}")
        except Exception as e:
            logger.error(f"Error finalizing transfer: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    async def transaction_history(self):
        """View transaction history."""
        console.print("[bold cyan]📥 Incoming Payments (Money I Received)[/bold cyan]")
        console.print()
        
        try:
            response = await paystack_service.list_transactions(per_page=10)
            transactions = response.get('data', [])
            
            if not transactions:
                self.display_info("No incoming payments found - no one has paid you yet")
                return
            
            table = Table(title="Incoming Payments")
            table.add_column("Date", style="cyan")
            table.add_column("Reference", style="white")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Status", style="yellow")
            table.add_column("Channel", style="dim")
            
            for transaction in transactions:
                date = transaction['created_at'][:10]
                reference = transaction['reference']
                amount = settings.format_amount(transaction['amount'], transaction['currency'])
                status = transaction['status']
                channel = transaction['channel']
                
                table.add_row(date, reference, amount, status, channel)
            
            console.print(table)
            
        except PaystackAPIError as e:
            self.display_error(f"Failed to fetch transactions: {e.message}")
        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            self.display_error(f"An unexpected error occurred: {str(e)}")
    
    def navigate_menu(self, options: List[str], title: str = "Select an option") -> int:
        """Navigate menu with arrow keys and Enter to select."""
        selected = 0
        
        while True:
            # Clear screen and display header
            console.clear()
            self.display_header()
            
            # Display title
            console.print(f"[bold]{title}:[/bold]")
            console.print()
            
            # Display options with selection cursor
            for i, option in enumerate(options):
                if i == selected:
                    # Highlight selected option
                    console.print(f"[bold cyan]→ {option}[/bold cyan]")
                else:
                    console.print(f"  {option}")
            
            console.print()
            console.print("[dim]Use ↑/↓ arrow keys to navigate, Enter to select, Esc to exit[/dim]")
            
            # Get key input
            key = msvcrt.getch()
            
            if key == b'\x1b':  # Escape key
                return -1
            elif key == b'\r':  # Enter key
                return selected
            elif key == b'\xe0':  # Arrow key prefix on Windows
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':  # Up arrow
                    selected = (selected - 1) % len(options)
                elif arrow_key == b'P':  # Down arrow
                    selected = (selected + 1) % len(options)
            elif key == b'\x03':  # Ctrl+C
                raise KeyboardInterrupt
    
    def run_menu(self):
        """Run the main CLI menu."""
        menu_options = [
            "🏦 Resolve Bank Account",
            "👤 Create Recipient", 
            "💰 Check Balance",
            "📤 My Outgoing Transfers (Money I Sent)",
            "💸 Initiate New Transfer",
            "🔐 Finalize Transfer (OTP)",
            "📥 Incoming Payments (Money I Received)",
            "❌ Exit"
        ]
        
        while self.running:
            # Use arrow key navigation
            choice = self.navigate_menu(menu_options, "Select an operation")
            
            if choice == -1 or choice == 7:  # Escape key or Exit
                self.running = False
                console.print("\n[bold green]Thank you for using Paystack CLI! 👋[/bold green]")
                break
            
            # Clear screen and execute choice
            console.clear()
            
            try:
                if choice == 0:
                    asyncio.run(self.resolve_bank_account())
                elif choice == 1:
                    asyncio.run(self.create_recipient())
                elif choice == 2:
                    asyncio.run(self.check_balance())
                elif choice == 3:
                    asyncio.run(self.list_transfers())
                elif choice == 4:
                    asyncio.run(self.initiate_transfer())
                elif choice == 5:
                    asyncio.run(self.finalize_transfer_menu())
                elif choice == 6:
                    asyncio.run(self.transaction_history())
                
                # Wait for user to continue
                console.print()
                input("Press Enter to continue...")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
                input("Press Enter to continue...")
            except Exception as e:
                logger.error(f"Unexpected error in menu: {str(e)}")
                console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
                input("Press Enter to continue...")


def main():
    """Main entry point for CLI application."""
    try:
        cli = PaystackCLI()
        cli.run_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]Application terminated by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        console.print(f"\n[red]Fatal error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main() 