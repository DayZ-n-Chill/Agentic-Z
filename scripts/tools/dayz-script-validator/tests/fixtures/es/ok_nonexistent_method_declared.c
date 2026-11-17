class MyCustomCrafting
{
    ref array<string> m_Ingredients;

    void AddIngredient(string classname)
    {
        m_Ingredients.Insert(classname);
    }

    void BuildList()
    {
        AddIngredient("Rag");
    }
}
