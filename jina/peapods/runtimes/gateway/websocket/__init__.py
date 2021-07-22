import os
from typing import Optional, Union

from .app import get_fastapi_app
from ...zmq.asyncio import AsyncNewLoopRuntime
from .....importer import ImportExtensions

if False:
    import multiprocessing
    import threading

__all__ = ['WebSocketRuntime']


class WebSocketRuntime(AsyncNewLoopRuntime):
    """Runtime for Websocket interface."""

    async def async_setup(self):
        """
        The async method setup the runtime.

        Setup the uvicorn server.
        """
        with ImportExtensions(required=True):
            from uvicorn import Config, Server

        class UviServer(Server):
            """The uvicorn server."""

            async def setup(self, sockets=None):
                """
                Setup uvicorn server.

                :param sockets: sockets of server.
                """
                config = self.config
                if not config.loaded:
                    config.load()
                self.lifespan = config.lifespan_class(config)
                self.install_signal_handlers()
                await self.startup(sockets=sockets)
                if self.should_exit:
                    return

            async def serve(self, **kwargs):
                """
                Start the server.

                :param kwargs: keyword arguments
                """
                await self.main_loop()

        from .....helper import extend_rest_interface

        self._server = UviServer(
            config=Config(
                app=extend_rest_interface(get_fastapi_app(self.args, self.logger)),
                host=self.args.host,
                port=self.args.port_expose,
                ws_max_size=1024 * 1024 * 1024,
                log_level=os.getenv('JINA_LOG_LEVEL', 'error').lower(),
            )
        )
        await self._server.setup()

    async def async_run_forever(self):
        """Running method of ther server."""
        await self._server.serve()

    async def async_cancel(self):
        """Stop the server."""
        self._server.should_exit = True
        await self._server.shutdown()

    @staticmethod
    def wait_ready_or_shutdown(
        timeout: Optional[float],
        ready_or_shutdown_event: Union['multiprocessing.Event', 'threading.Event'],
        **kwargs
    ):
        """
        Check if the runtime has successfully started

        :return: True if is ready or it needs to be shutdown
        """
        return ready_or_shutdown_event.wait(timeout)
