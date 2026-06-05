"""Tests for Maven detection (P1-T05)."""
from app.detect.maven_detector import detect

SINGLE_POM = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>
  <properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>
  </properties>
</project>
"""

MULTI_POM = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
    <module>core</module>
    <module>web</module>
  </modules>
</project>
"""


def test_single_module(tmp_path):
    (tmp_path / "pom.xml").write_text(SINGLE_POM, encoding="utf-8")
    (tmp_path / "src/main/java").mkdir(parents=True)
    (tmp_path / "src/test/java").mkdir(parents=True)
    p = detect(tmp_path)
    assert p.is_maven
    assert p.artifact_id == "demo"
    assert p.group_id == "com.example"
    assert p.version == "1.0.0"
    assert p.java_version == "1.8"
    assert not p.multi_module
    assert p.main_src == "src/main/java"
    assert p.test_src == "src/test/java"


def test_multi_module(tmp_path):
    (tmp_path / "pom.xml").write_text(MULTI_POM, encoding="utf-8")
    p = detect(tmp_path)
    assert p.is_maven
    assert p.multi_module
    assert p.modules == ["core", "web"]
    assert p.packaging == "pom"


def test_not_maven(tmp_path):
    (tmp_path / "build.gradle").write_text("// gradle", encoding="utf-8")
    p = detect(tmp_path)
    assert not p.is_maven
    assert "no pom.xml" in p.reason
