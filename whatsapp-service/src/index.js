import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} from '@whiskeysockets/baileys';
import express from 'express';
import pino from 'pino';
import qrcode from 'qrcode-terminal';

const logger = pino({ level: 'info' });
const app = express();
app.use(express.json());

let sock = null;
let isConnected = false;
let qrCodeData = null;

// Connection state
async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    logger: pino({ level: 'silent' }), // silent logs dari baileys
    printQRInTerminal: false,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    generateHighQualityLinkPreview: true,
  });

  // Event: connection update
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      qrCodeData = qr;
      logger.info('QR Code generated. Scan via /qr endpoint or terminal.');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const shouldReconnect =
        lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;

      logger.warn(`Connection closed. Reconnecting: ${shouldReconnect}`);
      isConnected = false;

      if (shouldReconnect) {
        setTimeout(connectToWhatsApp, 3000);
      }
    } else if (connection === 'open') {
      logger.info('✅ WhatsApp connected via Baileys!');
      isConnected = true;
      qrCodeData = null; // Clear QR setelah connected
      
      // Log user info
      try {
        const user = sock.user;
        if (user) {
          logger.info(`Logged in as: ${user.id} (${user.name || 'No name'})`);
        }
      } catch (e) {
        logger.warn('Could not get user info');
      }
    }
  });

  // Event: credentials update (save session)
  sock.ev.on('creds.update', saveCreds);
}

// API Endpoints
app.get('/health', (req, res) => {
  let userInfo = null;
  
  if (isConnected && sock && sock.user) {
    userInfo = {
      id: sock.user.id,
      name: sock.user.name || 'No name'
    };
  }
  
  res.json({
    status: 'ok',
    connected: isConnected,
    hasQr: !!qrCodeData,
    user: userInfo
  });
});

app.get('/qr', (req, res) => {
  if (isConnected) {
    return res.json({ status: 'already_connected' });
  }

  if (!qrCodeData) {
    return res.status(404).json({ error: 'No QR code available. Wait or restart service.' });
  }

  res.json({ qr: qrCodeData });
});

app.post('/send', async (req, res) => {
  if (!isConnected || !sock) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }

  const { to, message } = req.body;

  if (!to || !message) {
    return res.status(400).json({ error: 'Missing "to" or "message" field' });
  }

  try {
    // Format nomor: 628979755323@s.whatsapp.net or 120363XXXXX@g.us for group
    const jid = to.includes('@') ? to : `${to}@s.whatsapp.net`;
    
    // Check if it's a group
    const isGroup = jid.includes('@g.us');

    // Only verify for private chat, skip for groups
    if (!isGroup) {
      const [result] = await sock.onWhatsApp(jid);
      
      if (!result || !result.exists) {
        logger.error(`Number not registered on WhatsApp: ${jid}`);
        return res.status(400).json({
          error: 'Number not registered on WhatsApp',
          number: to,
          suggestion: 'Pastikan nomor sudah terdaftar di WhatsApp dan format benar (628979755323)'
        });
      }
      
      logger.info(`Sending message to ${jid} (verified: ${result.exists})`);
    } else {
      logger.info(`Sending message to group ${jid}`);
    }
    
    const sendResult = await sock.sendMessage(jid, { text: message });

    const recipientType = isGroup ? 'group' : 'private';
    logger.info(`Message sent successfully to ${recipientType}: ${jid}, messageId: ${sendResult.key.id}`);
    
    res.json({
      status: 'sent',
      messageId: sendResult.key.id,
      to: jid,
      verified: !isGroup,
      isGroup: isGroup
    });
  } catch (error) {
    logger.error(`Failed to send message: ${error.message}`);
    res.status(500).json({
      error: 'Failed to send message',
      details: error.message,
    });
  }
});

app.post('/logout', async (req, res) => {
  if (!sock) {
    return res.status(400).json({ error: 'Not connected' });
  }

  try {
    await sock.logout();
    isConnected = false;
    logger.info('Logged out from WhatsApp');
    res.json({ status: 'logged_out' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/verify', async (req, res) => {
  if (!isConnected || !sock) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }

  const { number } = req.body;

  if (!number) {
    return res.status(400).json({ error: 'Missing "number" field' });
  }

  try {
    const jid = number.includes('@s.whatsapp.net') ? number : `${number}@s.whatsapp.net`;
    const [result] = await sock.onWhatsApp(jid);

    if (!result) {
      return res.json({
        number,
        jid,
        exists: false,
        message: 'Unable to verify number'
      });
    }

    logger.info(`Number verification: ${jid} - exists: ${result.exists}`);
    
    res.json({
      number,
      jid: result.jid,
      exists: result.exists,
      message: result.exists ? 'Number is registered on WhatsApp' : 'Number not found on WhatsApp'
    });
  } catch (error) {
    logger.error(`Failed to verify number: ${error.message}`);
    res.status(500).json({
      error: 'Failed to verify number',
      details: error.message,
    });
  }
});

app.get('/groups', async (req, res) => {
  if (!isConnected || !sock) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }

  try {
    // Get all groups
    const groups = await sock.groupFetchAllParticipating();

    console.log(groups);
    
    const groupList = Object.values(groups).map(group => ({
      id: group.id,
      subject: group.subject,
      owner: group.owner,
      participants: group.participants?.length || 0,
      creation: group.creation,
      desc: group.desc,
    }));

    logger.info(`Fetched ${groupList.length} groups`);
    
    res.json({
      count: groupList.length,
      groups: groupList
    });
  } catch (error) {
    logger.error(`Failed to fetch groups: ${error.message}`);
    res.status(500).json({
      error: 'Failed to fetch groups',
      details: error.message,
    });
  }
});

// Start server
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  logger.info(`🚀 WhatsApp Baileys service running on port ${PORT}`);
  connectToWhatsApp();
});
