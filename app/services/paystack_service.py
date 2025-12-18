"""Paystack API Service for handling all Paystack operations."""

import httpx
from typing import Dict, List, Optional, Any, cast
from app.utils.logger import get_logger
from app.utils.config import settings

logger = get_logger("paystack_service")


class PaystackAPIError(Exception):
    """Custom exception for Paystack API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class PaystackService:
    """Service class for interacting with Paystack API."""
    
    def __init__(self):
        self.base_url = settings.paystack_base_url
        self.secret_key = settings.paystack_secret_key
        
        # Validate Paystack configuration
        if not self.secret_key or self.secret_key in ["sk_test_placeholder", "sk_test_your_secret_key_here", ""]:
            logger.warning("⚠️  Paystack secret key not configured or using placeholder value")
            logger.warning("⚠️  Paystack API calls will fail. Please set PAYSTACK_SECRET_KEY in environment variables")
        else:
            logger.info("✅ Paystack secret key configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request to Paystack API with retry logic and comprehensive error handling."""
        # Validate configuration before making request
        if not self.secret_key or self.secret_key in ["sk_test_placeholder", "sk_test_your_secret_key_here", ""]:
            error_msg = "Paystack API key not configured. Please set PAYSTACK_SECRET_KEY in environment variables."
            logger.error(error_msg)
            raise PaystackAPIError(message=error_msg, status_code=401)
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries + 1):
            try:
                # Add exponential backoff for retries
                if attempt > 0:
                    import asyncio
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.info(f"Retrying {method} {endpoint} in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(wait_time)
                
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=data,
                        params=params,
                        timeout=30.0
                    )
                    
                    logger.info(f"{method} {endpoint} - Status: {response.status_code} (attempt {attempt + 1})")
                    
                    # Handle different types of responses
                    try:
                        response_data = response.json()
                    except ValueError as json_error:
                        logger.error(f"Invalid JSON response: {json_error}")
                        if attempt < max_retries:
                            continue
                        raise PaystackAPIError(
                            message="Invalid JSON response from Paystack API",
                            status_code=response.status_code
                        )
                    
                    # Handle HTTP error status codes
                    if response.status_code >= 500:
                        # Server errors - retry
                        logger.warning(f"Server error {response.status_code}, will retry if attempts remain")
                        if attempt < max_retries:
                            continue
                        error_message = response_data.get("message", f"Server error {response.status_code}")
                        raise PaystackAPIError(
                            message=error_message,
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    
                    elif response.status_code >= 400:
                        # Client errors - don't retry
                        error_message = response_data.get("message", "Unknown client error occurred")
                        logger.error(f"Client error: {error_message}")
                        raise PaystackAPIError(
                            message=error_message,
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    
                    # Check Paystack-specific status field
                    if not response_data.get("status"):
                        error_message = response_data.get("message", "Request failed")
                        logger.error(f"Request failed: {error_message}")
                        
                        # Some Paystack errors might be worth retrying
                        if "network" in error_message.lower() or "timeout" in error_message.lower():
                            if attempt < max_retries:
                                continue
                        
                        raise PaystackAPIError(
                            message=error_message,
                            response_data=response_data
                        )
                    
                    # Success case
                    logger.debug(f"Successfully completed {method} {endpoint}")
                    return cast(Dict[str, Any], response_data)
                    
            except httpx.RequestError as e:
                logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue
                raise PaystackAPIError(f"Network error after {max_retries + 1} attempts: {str(e)}")
                
            except PaystackAPIError:
                # Don't retry on known PaystackAPIErrors unless it's a server error
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue
                raise PaystackAPIError(f"Unexpected error after {max_retries + 1} attempts: {str(e)}")
        
        # This should never be reached, but just in case
        raise PaystackAPIError("Maximum retry attempts exhausted")
    
    # Bank and Account Resolution Methods
    
    async def list_banks(self, currency: str = "NGN") -> List[Dict]:
        """Get list of banks for a specific currency."""
        logger.info(f"Fetching banks for currency: {currency}")
        
        response = await self._make_request(
            method="GET",
            endpoint="/bank",
            params={"currency": currency}
        )
        
        return cast(List[Dict], response.get("data", []))
    
    async def resolve_account(self, account_number: str, bank_code: str) -> Dict:
        """Resolve account number to get account name."""
        logger.info(f"Resolving account: {account_number} for bank: {bank_code}")
        
        response = await self._make_request(
            method="GET",
            endpoint="/bank/resolve",
            params={
                "account_number": account_number,
                "bank_code": bank_code
            }
        )
        
        return cast(Dict, response.get("data", {}))
    
    # Transfer Recipient Methods
    
    async def create_transfer_recipient(
        self,
        recipient_type: str,
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = "NGN",
        description: Optional[str] = None
    ) -> Dict:
        """Create a new transfer recipient."""
        logger.info(f"Creating transfer recipient: {name}")
        
        data = {
            "type": recipient_type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }
        
        if description:
            data["description"] = description
        
        response = await self._make_request(
            method="POST",
            endpoint="/transferrecipient",
            data=data
        )
        
        return cast(Dict, response.get("data", {}))
    
    async def list_transfer_recipients(
        self,
        per_page: int = 50,
        page: int = 1
    ) -> Dict:
        """Get list of transfer recipients."""
        logger.info(f"Fetching transfer recipients - Page {page}")
        
        response = await self._make_request(
            method="GET",
            endpoint="/transferrecipient",
            params={
                "perPage": str(per_page),  # Convert to string for API
                "page": str(page)  # Convert to string for API
            }
        )
        
        return cast(Dict, response)
    
    async def fetch_transfer_recipient(self, recipient_code: str) -> Dict:
        """Get details of a specific transfer recipient."""
        logger.info(f"Fetching recipient: {recipient_code}")
        
        response = await self._make_request(
            method="GET",
            endpoint=f"/transferrecipient/{recipient_code}"
        )
        
        return cast(Dict, response.get("data", {}))
    
    # Balance Methods
    
    async def get_balance(self) -> List[Dict]:
        """Get account balance."""
        logger.info("Fetching account balance")
        
        response = await self._make_request(
            method="GET",
            endpoint="/balance"
        )
        
        return cast(List[Dict], response.get("data", []))
    
    async def get_balance_ledger(
        self,
        per_page: int = 50,
        page: int = 1
    ) -> Dict:
        """Get balance ledger (transaction history)."""
        logger.info(f"Fetching balance ledger - Page {page}")
        
        response = await self._make_request(
            method="GET",
            endpoint="/balance/ledger",
            params={
                "perPage": str(per_page),  # Convert to string for API
                "page": str(page)  # Convert to string for API
            }
        )
        
        return cast(Dict, response)
    
    # Transfer Methods
    
    async def initiate_transfer(
        self,
        amount: int,
        recipient_code: str,
        reason: str,
        currency: str = "NGN",
        reference: Optional[str] = None
    ) -> Dict:
        """Initiate a transfer."""
        logger.info(f"Initiating transfer of {amount} to {recipient_code}")
        
        data = {
            "source": "balance",
            "amount": amount,
            "recipient": recipient_code,
            "reason": reason,
            "currency": currency,
        }
        
        if reference:
            data["reference"] = reference
        
        response = await self._make_request(
            method="POST",
            endpoint="/transfer",
            data=data
        )
        
        return cast(Dict, response.get("data", {}))
    
    async def finalize_transfer(self, transfer_code: str, otp: str) -> Dict:
        """Finalize transfer with OTP."""
        logger.info(f"Finalizing transfer: {transfer_code}")
        
        data = {
            "transfer_code": transfer_code,
            "otp": otp,
        }
        
        response = await self._make_request(
            method="POST",
            endpoint="/transfer/finalize_transfer",
            data=data
        )
        
        return cast(Dict, response.get("data", {}))
    
    async def list_transfers(
        self,
        per_page: int = 50,
        page: int = 1,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict:
        """Get list of transfers."""
        logger.info(f"Fetching transfers - Page {page}")
        
        params = {
            "perPage": str(per_page),  # Convert to string for API
            "page": str(page)  # Convert to string for API
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        response = await self._make_request(
            method="GET",
            endpoint="/transfer",
            params=params
        )
        
        return cast(Dict, response)
    
    async def fetch_transfer(self, transfer_code: str) -> Dict:
        """Get details of a specific transfer."""
        logger.info(f"Fetching transfer: {transfer_code}")
        
        response = await self._make_request(
            method="GET",
            endpoint=f"/transfer/{transfer_code}"
        )
        
        return cast(Dict, response.get("data", {}))
    
    async def verify_transfer(self, reference: str) -> Dict:
        """Verify transfer status by reference."""
        logger.info(f"Verifying transfer: {reference}")
        
        response = await self._make_request(
            method="GET",
            endpoint=f"/transfer/verify/{reference}"
        )
        
        return cast(Dict, response.get("data", {}))
    
    # Transaction Methods
    
    async def list_transactions(
        self,
        per_page: int = 50,
        page: int = 1,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict:
        """Get list of transactions."""
        logger.info(f"Fetching transactions - Page {page}")
        
        params = {
            "perPage": str(per_page),  # Convert to string for API
            "page": str(page)  # Convert to string for API
        }
        
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        response = await self._make_request(
            method="GET",
            endpoint="/transaction",
            params=params
        )
        
        return cast(Dict, response)
    
    async def verify_transaction(self, reference: str) -> Dict:
        """Verify transaction status by reference."""
        logger.info(f"Verifying transaction: {reference}")
        
        response = await self._make_request(
            method="GET",
            endpoint=f"/transaction/verify/{reference}"
        )
        
        return cast(Dict, response.get("data", {}))
    
    async def fetch_transaction(self, transaction_id: int) -> Dict:
        """Get details of a specific transaction."""
        logger.info(f"Fetching transaction: {transaction_id}")
        
        response = await self._make_request(
            method="GET",
            endpoint=f"/transaction/{transaction_id}"
        )
        
        return cast(Dict, response.get("data", {}))


# Create global service instance
paystack_service = PaystackService()

# Validate Paystack configuration on module load
try:
    from app.utils.service_validator import validate_paystack_config
    paystack_validation = validate_paystack_config()
    if not paystack_validation["valid"]:
        logger.error("⚠️  Paystack service initialized with configuration issues")
        for issue in paystack_validation["issues"]:
            logger.error(f"   - {issue}")
except Exception as e:
    logger.warning(f"Could not validate Paystack configuration: {e}") 