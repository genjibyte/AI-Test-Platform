package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class CalcTest {
    @Test void add() { assertEquals(5, new Calc().add(2, 3)); }
    @Test void max() { assertEquals(7, new Calc().max(7, 3)); }
}
