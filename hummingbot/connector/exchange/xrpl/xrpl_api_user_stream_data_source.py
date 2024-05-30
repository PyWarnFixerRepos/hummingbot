import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

from xrpl.clients import WebsocketClient
from xrpl.models import Subscribe

from hummingbot.connector.exchange.xrpl.xrpl_auth import XRPLAuth
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.xrpl.xrpl_exchange import XrplExchange


class XRPLAPIUserStreamDataSource(UserStreamTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 auth: XRPLAuth,
                 connector: 'XrplExchange'):
        super().__init__()
        self._connector = connector
        self._auth = auth

    async def listen_for_user_stream(self, output: asyncio.Queue):
        """
        Connects to the user private channel in the exchange using a websocket connection. With the established
        connection listens to all balance events and order updates provided by the exchange, and stores them in the
        output queue

        :param output: the queue to use to store the received messages
        """
        while True:
            try:
                subscribe = Subscribe(accounts=[self._auth.get_account()])

                with WebsocketClient(self._connector.node_url) as client:
                    client.send(subscribe)

                    for message in client:
                        await self._process_event_message(event_message=message, queue=output)
            except asyncio.CancelledError:
                self.logger().info("User stream listener task has been cancelled. Exiting...")
                raise
            except ConnectionError as connection_exception:
                self.logger().warning(f"The websocket connection was closed ({connection_exception})")
            except TimeoutError:
                self.logger().warning(
                    "Timeout error occurred while listening to user stream. Retrying after 5 seconds...")
            except Exception:
                self.logger().exception("Unexpected error while listening to user stream. Retrying after 5 seconds...")
            finally:
                await self._sleep(5.0)

    async def _process_event_message(self, event_message: Dict[str, Any], queue: asyncio.Queue):
        queue.put_nowait(event_message)