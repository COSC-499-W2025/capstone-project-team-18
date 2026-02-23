import java.util.ArrayList;
import java.util.List;
import java.io.File;

public class ExampleClass {
    private String name;
    private int age;

    public ExampleClass(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getAge() {
        return this.age;
    }

    public void setAge(int age) {
        this.age = age;
    }

    public static void main(String[] args) {
        ExampleClass example = new ExampleClass("John", 30);
        System.out.println("Name: " + example.getName());
        System.out.println("Age: " + example.getAge());
    }
}

class HelperClass {
    public void helperMethod() {
        System.out.println("This is a helper method");
    }

    private int calculate(int a, int b) {
        return a + b;
    }
}
