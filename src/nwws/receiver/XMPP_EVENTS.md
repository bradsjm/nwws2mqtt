## Event Flow from Connection to Disconnection

### **Connection Phase Events:**

1. **`"connecting"`** - Triggered at the start of `connect()` method
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L447
   self.event("connecting")
   ```

2. **`"reconnect_delay"`** - Triggered if there's a delay before connection attempts (with delay time as data)
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L462
   self.event('reconnect_delay', self._connect_loop_wait)
   ```

3. **`"connection_failed"`** - Triggered when connection attempts fail (with error details)
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L532-533
   self.event('connection_failed', 'No DNS record available for %s' % self.default_domain)
   ```
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L537
   self.event("connection_failed", e)
   ```

### **Successful Connection Events:**

4. **`"connected"`** - Triggered when TCP connection is established (via `self.event_when_connected`)
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L552
   self.event(self.event_when_connected)
   ```

5. **`"ssl_cert"`** - Triggered when SSL certificate is received (with PEM certificate data)
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L567
   self.event('ssl_cert', pem_cert)
   ```

6. **`"tls_success"`** - Triggered when TLS handshake succeeds
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L571
   self.event('tls_success')
   ```

7. **`"ssl_invalid_chain"`** - Triggered when SSL certificate chain validation fails
   ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L868
   self.event('ssl_invalid_chain', e)
   ```

### **Stream Handling Events:**

8. **Stream start** - When the XML stream header is received, `start_stream_handler()` is called (which can be overridden to trigger custom events)

9. **Stanza events** - Individual stanzas trigger events through `_spawn_event()` method, which processes incoming XML and converts them to stanza objects that get handled by registered handlers

### **Send Queue Events:**

10. **`"stanza_not_sent"`** - Triggered when a stanza cannot be sent due to disconnection
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L1359
    self.event('stanza_not_sent', data)
    ```

### **Disconnection Phase Events:**

11. **`"eof_received"`** - Triggered when the remote end properly closes the TCP connection
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L639
    self.event("eof_received")
    ```

12. **`"session_end"`** - Triggered before disconnection if `end_session_on_disconnect` is True
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L655
    self.event('session_end')
    ```

13. **`"disconnected"`** - Triggered when the connection is lost or explicitly disconnected (with reason or exception)
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L657
    self.event("disconnected", self.disconnect_reason or exception)
    ```
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L725
    self.event("disconnected", reason)
    ```

14. **`"killed"`** - Triggered when the connection is forcibly aborted
    ```nwws2mqtt/.venv/lib/python3.13/site-packages/slixmpp/xmlstream/xmlstream.py#L766
    self.event("killed")
    ```

## **Typical Event Sequence:**

**Successful Connection:**
1. `"connecting"`
2. `"connected"`
3. `"ssl_cert"` (if SSL/TLS)
4. `"tls_success"` (if TLS)
5. Stream processing begins
6. Eventually: `"session_end"` → `"disconnected"`

**Failed Connection:**
1. `"connecting"`
2. `"reconnect_delay"` (if retrying)
3. `"connection_failed"` (one or more times)
4. Eventually: `"disconnected"`

**Aborted Connection:**
1. Any of the above events
2. `"killed"` (if forcibly aborted)
