<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://cnx.rice.edu/cnxml"
  xmlns:cnx="http://cnx.rice.edu/cnxml"
  xmlns:md="http://cnx.rice.edu/mdml"
  xmlns:bib="http://bibtexml.sf.net/"
  xmlns:m="http://www.w3.org/1998/Math/MathML"
  xmlns:q="http://cnx.rice.edu/qml/1.0"
  version="1.0">

<xsl:variable name="smallcase" select="'abcdefghijklmnopqrstuvwxyz'" />
<xsl:variable name="uppercase" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ'" />

<!-- WORKAROUND - fix bug: duplicated figures show on top after imported docx -->
<xsl:template match="cnx:figure">
  <xsl:param name='type'>
    <xsl:value-of select="substring-after(cnx:media/cnx:image/@mime-type, '/')"/>
  </xsl:param>
  <xsl:param name='ext'>
    <xsl:value-of select="substring-after(cnx:media/cnx:image/@src, '.')"/>
  </xsl:param>
  <xsl:variable name='lowerext'>
    <xsl:value-of select="translate($ext, $uppercase, $smallcase)" />
  </xsl:variable>
  <xsl:variable name='lowerdoubletype'>
    <xsl:value-of select="translate(concat($type, '.', $type), $uppercase, $smallcase)" />
  </xsl:variable>
  <xsl:choose>
    <xsl:when test="$lowerext = $lowerdoubletype">
    </xsl:when>
    <xsl:otherwise>
      <figure>
        <xsl:apply-templates select="@*|node()"/>
      </figure>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- WORKAROUND - fix bug: remove Untitled Document title on top -->
<xsl:template match="cnx:title">
  <xsl:choose>
    <xsl:when test="text() = 'Untitled Document'">
    </xsl:when>
    <xsl:otherwise>
      <title>
        <xsl:apply-templates select="@*|node()"/>
      </title>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="@*|node()">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
</xsl:template>

</xsl:stylesheet>

