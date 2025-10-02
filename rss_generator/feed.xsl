<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <html>
      <head>
        <title><xsl:value-of select="/rss/channel/title"/> - RSS Feed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <style>
          * {
            box-sizing: border-box;
          }

          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
          }

          .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          }

          .header h1 {
            margin: 0 0 10px 0;
            font-size: 2em;
          }

          .header p {
            margin: 0;
            opacity: 0.9;
          }

          .feed-info {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          }

          .feed-info h2 {
            margin-top: 0;
            color: #667eea;
          }

          .items {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          }

          .item {
            padding: 25px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
          }

          .item:last-child {
            border-bottom: none;
          }

          .item:hover {
            background: #f9f9f9;
          }

          .item h3 {
            margin: 0 0 10px 0;
          }

          .item h3 a {
            color: #333;
            text-decoration: none;
            font-size: 1.3em;
          }

          .item h3 a:hover {
            color: #667eea;
          }

          .item-meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
          }

          .item-category {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-right: 10px;
          }

          .item-description {
            color: #555;
            line-height: 1.7;
          }

          .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
          }

          .rss-icon {
            width: 40px;
            height: 40px;
            display: inline-block;
            margin-right: 10px;
            vertical-align: middle;
          }

          @media (max-width: 600px) {
            body {
              padding: 10px;
            }

            .header {
              padding: 20px;
            }

            .header h1 {
              font-size: 1.5em;
            }

            .item {
              padding: 15px;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>
            <svg class="rss-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="6.18" cy="17.82" r="2.18"/>
              <path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
            </svg>
            <xsl:value-of select="/rss/channel/title"/>
          </h1>
          <p><xsl:value-of select="/rss/channel/description"/></p>
        </div>

        <div class="feed-info">
          <h2>📡 RSS Feed</h2>
          <p>This is an RSS feed. To subscribe, copy the URL from your browser's address bar and paste it into your RSS reader.</p>
          <p><strong>Feed URL:</strong> <xsl:value-of select="/rss/channel/link/@href"/></p>
        </div>

        <div class="items">
          <xsl:for-each select="/rss/channel/item">
            <div class="item">
              <h3>
                <a>
                  <xsl:attribute name="href">
                    <xsl:value-of select="link"/>
                  </xsl:attribute>
                  <xsl:value-of select="title"/>
                </a>
              </h3>

              <div class="item-meta">
                <xsl:if test="category">
                  <span class="item-category">
                    <xsl:value-of select="category"/>
                  </span>
                </xsl:if>
                <xsl:if test="pubDate">
                  <span>📅 <xsl:value-of select="pubDate"/></span>
                </xsl:if>
              </div>

              <div class="item-description">
                <xsl:value-of select="description"/>
              </div>
            </div>
          </xsl:for-each>
        </div>

        <div class="footer">
          <p>Generated by RSS Generator • <a href="https://github.com/pedromcaraujo/rss-generator" style="color: #667eea;">View on GitHub</a></p>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
