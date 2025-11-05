running PC game on android phone via box64, wine, dxvk and etc.

# Install and Config Winlator on Android Phone

1. Downlload and install Winlator variation from: https://github.com/coffincolors/winlator

2. adb push your game bianries to /sdcard/Download/ folder, which is mapped to D: drive in the container.

3. Create an container in Winlator, selecting Turnip as Graphics Driver.

4. Launch the container. Run the game on D: drive.

5. Enjoy.


# Install and Config Termux

1. Run `./install-termux.py` to install termux and termux-x11 apps. Follow instructions and prompt on phone to continue and finish the installtion.

2. Launch Termux app

3. Inside Termud, run the following commands.

    ```bash
    pkg update
    pkg install -y openssh
    sshd # launch sshd service
    whoami # this is to show the current user name
    passwd # this is to genereta new pasword for login
    ```

    (You may connect to termux via scrcpy.py. This make typing commands in termux much easier)

4. Update the user name field in termux-user.txt to match the username return by `whoami` command in the previous step.

5. Forward termux openssh port to local port via adb:

    ```bash
    adb forward tcp:8022 tcp:8022
    ```

    This command forwards the termux 8022 port (which is what the sshd listens to on your phone), to your localhost 8022 port.

6. Copy your ssh public key to termux for easier login:

    ```bash
    ./termux-ssh-login.py --copy-key
    ```

    It'll ask for the password. Use the one you generated in step #3 with `passwd` command.


# Install wine:amd64 Inside Termux

1. Install and launch an debian distro in termux

    ```bash
    pkg install proot-distro
    proot-distro install debian
    proot-distro login debian
    ```

2. From within the debian distro, Download and extract wine amd64 and its dependencies:

    ```bash
    # register wine:amd64
    dpkg --add-architecture amd64
    dpkg --add-architecture i386
    apt update
    apt install wget gpg
    mkdir -pm755 /etc/apt/keyrings
    rm -f /etc/apt/keyrings/winehq-archive.key
    wget -O - https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key -
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/trixie/winehq-trixie.sources
    apt update
    # download wine:amd64 to /tmp/windl
    mkdir -p /tmp/winedl && cd /tmp/winedl
    apt-get --download-only install -y --install-recommends winehq-stable:amd64
    cp -v /var/cache/apt/archives/*.deb /tmp/winedl/
    # extact everything to /opt/wine64-root
    mkdir -p /opt/wine64-root
    for f in /tmp/winedl/*_amd64.deb; do
        echo dpkg -x "$f" /opt/wine64-root
        dpkg -x "$f" /opt/wine64-root
    done
    # all done. exit debian distro
    exit
    ```

3. Now, under normal termux prompt (not in debian distro), move the extracted wine:amd64 binaries to your local home folder

    ```
    mv /data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/debian/opt/wine64-root ~/wine64-root


4. Overall simulation flowchart

```mermaid
graph TD
    A[PC Game Executable D3D11/D3D12, Win32 APIs, Input, Audio] --> B[CPU Translation<br/>box64 / FEX / QEMU]
    B --> C[Wine / Proton / Winelib<br/>Implements Win32/NT APIs]
    C --> D[DXVK / vkd3d-proton<br/>D3D → Vulkan translation]
    D --> E[Vulkan Runtime<br/>libvulkan + GPU driver]
    E --> F[Presentation<br/>ANativeWindow → SurfaceFlinger → Display]

    A --> G[Input Mapping<br/>Android → XInput/RawInput]
    A --> H[Audio Path<br/>XAudio2 → AAudio/OpenSL ES]
    C --> I[Filesystem & Sandbox<br/>Wine prefix, storage permissions]

    subgraph Android System Layer
        G
        H
        I
        E
        F
    end

    subgraph Compatibility & Translation
        B
        C
        D
    end

    subgraph Windows Game Layer
        A
    end

    classDef layer fill:#2f2f2f,stroke:#555,color:#fff;
    class A,B,C,D,E,F,G,H,I layer;
```