<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://cnx.rice.edu/cnxml"
  xmlns:cnx="http://cnx.rice.edu/cnxml"
  xmlns:md="http://cnx.rice.edu/mdml"
  xmlns:bib="http://bibtexml.sf.net/"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:q="http://cnx.rice.edu/qml/1.0"
  version="1.0"
  exclude-result-prefixes="cnx">

<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

<xsl:strip-space elements="*"/>

<!-- makes XML pretty indenting, works only with libxslt, not lxml! -->

<xsl:template match="@*|node()">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
</xsl:template>

<!-- WORKAROUND - fix bug: duplicated figures show on top after imported docx -->
<xsl:template match="cnx:figure">
  <xsl:param name='type'>
    <xsl:value-of select="substring-after(cnx:media/cnx:image/@mime-type, '/')"/>
  </xsl:param>
  <xsl:param name='ext'>
    <xsl:value-of select="substring-after(cnx:media/cnx:image/@src, '.')"/>
  </xsl:param>
  <xsl:choose>
    <xsl:when test="lower-case($ext) = concat($type, '.', $type)">
    </xsl:when>
    <xsl:otherwise>
      <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
      </xsl:copy>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:stylesheet>