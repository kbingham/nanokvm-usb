# Next steps

- Hook up a capture system to grab MJPEG from the UVC device (ideally with automatic detection of which UVC device is the Nano-KVM
  - Capture size should be configurable (Target will detect that size as the monitor?)
  - Zero copy whereever possible - so ideally decode straight to a GL surface.

- Mouse control
  - When video is implemented we need both relative and absolute mouse movement
    control to be added.
  - We might even want a menu box to allow configuration of how the app interacts

- Additional Keys
  - Some keys can not be captured to transmit. There should be a panel
    to support sending hotkeys that would otherwise be intercepted
    by the native linux compositor. (Printscreen, hotkeys, ...)

