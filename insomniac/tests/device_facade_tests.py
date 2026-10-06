import unittest

from uiautomator2.exceptions import RPCError, UiObjectNotFoundError

from insomniac.device_facade import DeviceFacade


class FakeDeviceV2:
    """Mimics the parts of uiautomator2 3.x Device used by DeviceFacade, without a real phone."""

    def __init__(self, error=None, alive=True):
        self.error = error
        self.alive = alive

    def __call__(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        return FakeViewV2(self.error)

    def _check_alive(self):
        return self.alive


class FakeViewV2:
    def __init__(self, error):
        self.error = error

    def click(self, *args, **kwargs):
        raise self.error


def create_facade(device_v2):
    facade = DeviceFacade.__new__(DeviceFacade)
    facade.device_id = None
    facade.app_id = "com.instagram.android"
    facade.deviceV1 = None
    facade.deviceV2 = device_v2
    return facade


class DeviceFacadeTests(unittest.TestCase):

    def test_find_wraps_uiautomator2_rpc_error(self):
        facade = create_facade(FakeDeviceV2(error=RPCError("boom")))
        with self.assertRaises(DeviceFacade.JsonRpcError):
            facade.find(resourceId="com.instagram.android:id/button")

    def test_find_wraps_ui_object_not_found(self):
        facade = create_facade(FakeDeviceV2(error=UiObjectNotFoundError("not found")))
        with self.assertRaises(DeviceFacade.JsonRpcError):
            facade.find(text="Follow")

    def test_is_alive_uses_uiautomator2_3_api(self):
        self.assertTrue(create_facade(FakeDeviceV2(alive=True)).is_alive())
        self.assertFalse(create_facade(FakeDeviceV2(alive=False)).is_alive())


if __name__ == '__main__':
    unittest.main()
